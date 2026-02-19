import cv2


def detect_largest_face(image_bgr):
    """
    Detect the largest frontal face in an image.
    Returns (x, y, w, h) or None.
    """
    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)

    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)

    faces = face_cascade.detectMultiScale(
        gray,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(80, 80),
    )

    if len(faces) == 0:
        return None

    # Pick the largest detected face for best stability.
    largest = max(faces, key=lambda rect: rect[2] * rect[3])
    x, y, w, h = [int(v) for v in largest]
    return x, y, w, h