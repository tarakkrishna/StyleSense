import json
import os
import re
from pathlib import Path
from uuid import uuid4

import cv2
import requests
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS

load_dotenv()

from face_detect import detect_largest_face
from product_search import search_fashion_products
from skin_tone import detect_skin_tone

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL = os.getenv("MODEL", "llama-3.3-70b-versatile")

app = Flask(__name__)
CORS(app)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def _json_error(message, status_code=400):
    return jsonify({"success": False, "error": message}), status_code


def _build_prompt(skin_tone, gender, occasion, season):
    return (
        "Generate personalized fashion styling advice.\n"
        f"Skin tone: {skin_tone}\n"
        f"Gender: {gender}\n"
        f"Occasion: {occasion}\n"
        f"Season: {season}\n\n"
        "Return ONLY valid JSON in this shape:\n"
        "{\n"
        '  "mandatory_outfit": {\n'
        '    "top": "...",\n'
        '    "bottom": "...",\n'
        '    "footwear": "..."\n'
        "  },\n"
        '  "outfit": ["..."],\n'
        '  "colors": ["...", "..."],\n'
        '  "accessories": ["...", "..."],\n'
        '  "hairstyle": "...",\n'
        '  "why_it_works": "..."\n'
        "}\n\n"
        "Rules:\n"
        "1) top, bottom, and footwear are compulsory.\n"
        "2) accessories are optional extras.\n"
    )


def _call_groq(prompt):
    if not GROQ_API_KEY or GROQ_API_KEY == "your_key_here":
        raise RuntimeError("GROQ_API_KEY is missing. Update backend/.env with a valid key.")

    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {GROQ_API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": [
            {
                "role": "system",
                "content": "You are a professional fashion stylist. Follow requested output format strictly.",
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.7,
        "max_tokens": 700,
    }

    response = requests.post(url, headers=headers, json=payload, timeout=30)
    response.raise_for_status()

    data = response.json()
    content = data["choices"][0]["message"]["content"]

    # Parse robustly: handle direct JSON, fenced JSON, or extra leading/trailing text.
    try:
        return _parse_model_json(content)
    except json.JSONDecodeError:
        raise json.JSONDecodeError("Model returned invalid JSON.", content, 0)


def _parse_model_json(content):
    text = (content or "").strip()
    if not text:
        raise json.JSONDecodeError("Empty response from model.", text, 0)

    # 1) Direct JSON.
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # 2) JSON inside markdown code block.
    fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, flags=re.IGNORECASE)
    if fence_match:
        fenced = fence_match.group(1).strip()
        try:
            return json.loads(fenced)
        except json.JSONDecodeError:
            pass

    # 3) Best-effort: parse the first JSON object slice.
    start = text.find("{")
    end = text.rfind("}")
    if start != -1 and end != -1 and end > start:
        return json.loads(text[start : end + 1])

    raise json.JSONDecodeError("No JSON object found in model output.", text, 0)


def _as_list(value):
    if isinstance(value, list):
        return [str(item) for item in value]
    if isinstance(value, str) and value.strip():
        # Convert comma/newline separated string into a list.
        parts = [p.strip(" -\t\r\n") for p in re.split(r"[,\n]+", value) if p.strip()]
        return parts
    return []


def _as_text(value):
    if isinstance(value, str):
        return value
    if value is None:
        return ""
    return str(value)


def _normalize_mandatory_outfit(ai_result):
    mandatory = ai_result.get("mandatory_outfit")
    if not isinstance(mandatory, dict):
        mandatory = {}

    top = _as_text(mandatory.get("top", "")).strip()
    bottom = _as_text(mandatory.get("bottom", "")).strip()
    footwear = _as_text(mandatory.get("footwear", "") or mandatory.get("footware", "")).strip()

    outfit_lines = _as_list(ai_result.get("outfit", []))

    # Fallback extraction from outfit text if model misses mandatory fields.
    if outfit_lines:
        for line in outfit_lines:
            lower = line.lower()
            if not footwear and any(k in lower for k in ["shoe", "sneaker", "loafer", "heel", "boot", "sandal"]):
                footwear = line
            elif not bottom and any(k in lower for k in ["jean", "trouser", "pant", "chino", "skirt", "short"]):
                bottom = line
            elif not top and any(k in lower for k in ["shirt", "top", "tee", "t-shirt", "blouse", "blazer", "jacket", "kurta"]):
                top = line

    # Positional fallback as last resort.
    if not top and outfit_lines:
        top = outfit_lines[0]
    if not bottom and len(outfit_lines) > 1:
        bottom = outfit_lines[1]
    if not footwear and len(outfit_lines) > 2:
        footwear = outfit_lines[2]

    # Hard fallback to guarantee compulsory fields.
    if not top:
        top = "Well-fitted neutral top"
    if not bottom:
        bottom = "Clean tailored bottom"
    if not footwear:
        footwear = "Versatile footwear matching the occasion"

    mandatory_outfit = {
        "top": top,
        "bottom": bottom,
        "footwear": footwear,
        "footware": footwear,
    }
    return mandatory_outfit


def _build_product_queries(ai_result, gender, occasion, season):
    mandatory = ai_result.get("mandatory_outfit", {})
    outfit = [
        _as_text(mandatory.get("top", "")).strip(),
        _as_text(mandatory.get("bottom", "")).strip(),
        _as_text(mandatory.get("footwear", "")).strip(),
    ] + _as_list(ai_result.get("outfit", []))
    outfit = [item for item in outfit if item]
    accessories = _as_list(ai_result.get("accessories", []))
    joined = " ".join(outfit + accessories).lower()

    # Map common fashion item keywords to clean search queries.
    item_map = {
        "blazer": f"{gender} {occasion} blazer {season}",
        "jeans": f"{gender} denim jeans slim fit {season}",
        "trouser": f"{gender} tailored trousers {season}",
        "shirt": f"{gender} casual shirt {season}",
        "dress": f"{gender} {occasion} dress {season}",
        "skirt": f"{gender} midi skirt {season}",
        "kurta": f"{gender} kurta {season}",
        "jacket": f"{gender} jacket {season}",
        "shoes": f"{gender} fashion shoes {occasion}",
        "heels": f"{gender} heels {occasion}",
        "sneakers": f"{gender} sneakers {season}",
        "loafer": f"{gender} loafers {occasion}",
        "bag": f"{gender} handbag {occasion}",
        "watch": f"{gender} watch {occasion}",
    }

    queries = []
    for keyword, query in item_map.items():
        if keyword in joined:
            queries.append(query)

    if not queries:
        # Fallback: search directly from first outfit lines.
        queries = [f"{gender} {line} {occasion} {season}" for line in outfit[:3] if line.strip()]

    if not queries:
        queries = [f"{gender} {occasion} fashion outfit {season}"]

    return queries[:4]


def _fetch_products(ai_result, gender, occasion, season):
    queries = _build_product_queries(ai_result, gender, occasion, season)
    products = []
    seen_links = set()

    for query in queries:
        results = search_fashion_products(query, limit=6)
        for item in results:
            link = _as_text(item.get("product_link")).strip()
            if not link or link in seen_links:
                continue
            seen_links.add(link)
            products.append(item)
            if len(products) >= 16:
                return products

    return products


@app.get("/health")
def health():
    return jsonify({"success": True, "message": "StyleAI backend is running."})


@app.post("/upload")
def upload_image():
    if "image" not in request.files:
        return _json_error("No image file found in request. Use form-data key: image.", 400)

    image_file = request.files["image"]
    if not image_file or image_file.filename == "":
        return _json_error("No image selected.", 400)

    if not allowed_file(image_file.filename):
        return _json_error("Unsupported file format. Use png, jpg, jpeg, or webp.", 400)

    extension = image_file.filename.rsplit(".", 1)[1].lower()
    filename = f"{uuid4().hex}.{extension}"
    filepath = UPLOAD_DIR / filename
    image_file.save(filepath)

    image_bgr = cv2.imread(str(filepath))
    if image_bgr is None:
        return _json_error("Failed to read uploaded image.", 400)

    face_rect = detect_largest_face(image_bgr)
    if not face_rect:
        return _json_error("No face detected. Please upload a clear front-facing image.", 422)

    try:
        tone_result = detect_skin_tone(image_bgr, face_rect)
    except Exception as exc:
        return _json_error(f"Skin tone detection failed: {str(exc)}", 500)

    x, y, w, h = face_rect

    return jsonify(
        {
            "success": True,
            "filename": filename,
            "face_box": {"x": x, "y": y, "w": w, "h": h},
            "skin_tone": tone_result["skin_tone"],
            "average_rgb": tone_result["average_rgb"],
        }
    )


@app.post("/recommend")
def recommend():
    body = request.get_json(silent=True) or {}

    required_fields = ["skin_tone", "gender", "occasion", "season"]
    missing = [f for f in required_fields if not body.get(f)]
    if missing:
        return _json_error(f"Missing required fields: {', '.join(missing)}", 400)

    prompt = _build_prompt(
        skin_tone=body["skin_tone"],
        gender=body["gender"],
        occasion=body["occasion"],
        season=body["season"],
    )

    try:
        ai_result = _call_groq(prompt)
    except requests.RequestException as exc:
        return _json_error(f"Groq API request failed: {str(exc)}", 502)
    except json.JSONDecodeError:
        return _json_error("Model returned invalid JSON. Please retry.", 502)
    except Exception as exc:
        return _json_error(str(exc), 500)

    mandatory_outfit = _normalize_mandatory_outfit(ai_result)
    outfit_list = [
        mandatory_outfit["top"],
        mandatory_outfit["bottom"],
        mandatory_outfit["footwear"],
    ]
    # Keep any extra outfit lines after compulsory items.
    extras = _as_list(ai_result.get("outfit", []))
    for item in extras:
        if item and item not in outfit_list:
            outfit_list.append(item)

    ai_recommendation = {
        "mandatory_outfit": mandatory_outfit,
        "outfit": outfit_list,
        "colors": _as_list(ai_result.get("colors", [])),
        "accessories": _as_list(ai_result.get("accessories", [])),
        "hairstyle": _as_text(ai_result.get("hairstyle", "")),
        "why_it_works": _as_text(ai_result.get("why_it_works", "")),
    }

    products = []
    product_error = None
    try:
        products = _fetch_products(
            ai_recommendation,
            body["gender"],
            body["occasion"],
            body["season"],
        )
    except Exception as exc:
        product_error = str(exc)

    response = {
        "success": True,
        "ai_recommendation": ai_recommendation,
        "products": products,
    }
    if product_error:
        response["product_warning"] = f"Product search unavailable: {product_error}"
    return jsonify(response)


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
