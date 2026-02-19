import numpy as np


def _clip_region(y1, y2, x1, x2, h, w):
    y1 = max(0, min(h, y1))
    y2 = max(0, min(h, y2))
    x1 = max(0, min(w, x1))
    x2 = max(0, min(w, x2))
    return y1, y2, x1, x2


def _average_cheek_color(face_roi_bgr):
    """
    Sample left and right cheek regions and return average RGB color.
    """
    h, w, _ = face_roi_bgr.shape

    # Relative cheek windows tuned for frontal faces.
    left = _clip_region(
        int(h * 0.45),
        int(h * 0.72),
        int(w * 0.10),
        int(w * 0.35),
        h,
        w,
    )
    right = _clip_region(
        int(h * 0.45),
        int(h * 0.72),
        int(w * 0.65),
        int(w * 0.90),
        h,
        w,
    )

    ly1, ly2, lx1, lx2 = left
    ry1, ry2, rx1, rx2 = right

    left_patch = face_roi_bgr[ly1:ly2, lx1:lx2]
    right_patch = face_roi_bgr[ry1:ry2, rx1:rx2]

    patches = [p for p in (left_patch, right_patch) if p.size > 0]
    if not patches:
        # Fallback to full face region if cheek patches are empty.
        patches = [face_roi_bgr]

    merged = np.vstack([p.reshape(-1, 3) for p in patches])
    # BGR -> RGB
    avg_bgr = np.mean(merged, axis=0)
    avg_rgb = avg_bgr[::-1]
    return tuple(int(c) for c in avg_rgb)


def _map_to_tone(avg_rgb):
    """
    Map average skin brightness to broad skin tone categories.
    """
    r, g, b = avg_rgb

    # Perceived luminance approximation.
    brightness = 0.299 * r + 0.587 * g + 0.114 * b

    if brightness >= 200:
        return "fair"
    if brightness >= 165:
        return "medium"
    if brightness >= 135:
        return "olive"
    if brightness >= 105:
        return "brown"
    return "deep"


def detect_skin_tone(image_bgr, face_rect):
    """
    Given a BGR image and face bounding box, return tone and avg RGB.
    """
    x, y, w, h = face_rect
    face_roi = image_bgr[y : y + h, x : x + w]

    if face_roi.size == 0:
        raise ValueError("Face ROI is empty. Cannot detect skin tone.")

    avg_rgb = _average_cheek_color(face_roi)
    tone = _map_to_tone(avg_rgb)

    return {
        "skin_tone": tone,
        "average_rgb": {
            "r": avg_rgb[0],
            "g": avg_rgb[1],
            "b": avg_rgb[2],
        },
    }