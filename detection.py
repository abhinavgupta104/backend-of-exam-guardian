"""
Lightweight frame analysis utilities for ProctorGuard.
Uses OpenCV Haar cascades to detect faces and returns basic violation signals.
"""

import base64
from typing import Dict, Optional

import cv2
import numpy as np


def _decode_base64_image(image_base64: str) -> Optional[np.ndarray]:
    """Decode a base64 image string into a BGR image matrix."""
    if not image_base64:
        return None

    cleaned = image_base64.strip()
    if "," in cleaned:
        cleaned = cleaned.split(",", 1)[1]

    try:
        image_bytes = base64.b64decode(cleaned)
    except (ValueError, base64.binascii.Error):
        return None

    image_array = np.frombuffer(image_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)
    return image


def compress_image(image: np.ndarray) -> Optional[str]:
    """
    Resize and compress an image, returning a base64 JPEG string.
    """
    if image is None:
        return None

    resized = cv2.resize(image, (640, 480))
    success, buffer = cv2.imencode(".jpg", resized, [int(cv2.IMWRITE_JPEG_QUALITY), 75])
    if not success:
        return None

    encoded = base64.b64encode(buffer.tobytes()).decode("utf-8")
    return encoded


def analyze_frame(image_base64: str) -> Dict[str, object]:
    """
    Analyze a webcam frame and return a basic proctoring signal.
    """
    image = _decode_base64_image(image_base64)
    if image is None:
        return {
            "alert": False,
            "reason": None,
            "severity": None,
            "violation_type": None,
            "compressed_image": None,
        }

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    cascade_path = f"{cv2.data.haarcascades}haarcascade_frontalface_default.xml"
    face_cascade = cv2.CascadeClassifier(cascade_path)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(60, 60))

    alert = False
    reason = None
    severity = None
    violation_type = None

    if len(faces) == 0:
        alert = True
        reason = "No face detected"
        severity = "warning"
        violation_type = "no_face"
    elif len(faces) > 1:
        alert = True
        reason = "Multiple faces detected"
        severity = "critical"
        violation_type = "multiple_faces"

    return {
        "alert": alert,
        "reason": reason,
        "severity": severity,
        "violation_type": violation_type,
        "compressed_image": compress_image(image),
    }
