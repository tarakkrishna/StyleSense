import os

import serpapi

def _as_text(value):
    if value is None:
        return ""
    return str(value)


def search_fashion_products(query, limit=8):
    """
    Search Google Shopping via SerpAPI and return normalized product entries.

    Return format:
    [
      {
        "title": "...",
        "price": "...",
        "image_url": "...",
        "product_link": "...",
        "source_store": "..."
      }
    ]
    """
    serpapi_key = (
        os.getenv("SERPAPI_API_KEY", "").strip()
        or os.getenv("SERPAPI_KEY", "").strip()
    )
    if not serpapi_key or serpapi_key.lower().startswith("your_"):
        raise RuntimeError("SerpAPI key missing. Set SERPAPI_API_KEY (or SERPAPI_KEY) in backend/.env")

    params = {
        "engine": "google_shopping",
        "q": query,
        "api_key": serpapi_key,
        "hl": "en",
        "gl": "us",
        "num": max(1, min(int(limit), 20)),
    }

    data = _run_serpapi_query(params)

    results = data.get("shopping_results", [])
    products = []
    seen_links = set()

    for item in results:
        link = _as_text(item.get("product_link") or item.get("link")).strip()
        if not link or link in seen_links:
            continue
        seen_links.add(link)

        product = {
            "title": _as_text(item.get("title")).strip() or "Fashion Item",
            "price": _as_text(item.get("price") or item.get("extracted_price") or "N/A").strip(),
            "image_url": _as_text(item.get("thumbnail") or item.get("image") or "").strip(),
            "product_link": link,
            "source_store": _as_text(item.get("source") or "Store").strip(),
        }
        products.append(product)

        if len(products) >= limit:
            break

    return products


def _run_serpapi_query(params):
    """
    Support both SerpAPI Python clients:
    - legacy google-search-results: GoogleSearch(params).get_dict()
    - newer serpapi client: serpapi.search(params).as_dict()
    """
    try:
        from serpapi import GoogleSearch  # type: ignore

        return GoogleSearch(params).get_dict()
    except Exception:
        result = serpapi.search(params)
        if hasattr(result, "as_dict"):
            return result.as_dict()
        if isinstance(result, dict):
            return result
        return {}
