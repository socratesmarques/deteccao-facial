"""LBF landmarks on the selected face only; invalid measurements fail closed."""
from __future__ import annotations

import cv2
import numpy as np

from app_paths import MODELS_DIR

LBF_MODEL = MODELS_DIR / 'lbfmodel.yaml'


def eye_aspect_ratio(points):
    points = np.asarray(points, dtype=np.float32)
    if points.shape != (6, 2) or not np.isfinite(points).all():
        return None
    width = float(np.linalg.norm(points[0] - points[3]))
    if width < 8:
        return None
    return float((np.linalg.norm(points[1] - points[5]) +
                  np.linalg.norm(points[2] - points[4])) / (2 * width))


class EyeLandmarks:
    def __init__(self, model_path=LBF_MODEL):
        if not model_path.is_file():
            raise RuntimeError('Modelo de piscadas ausente. Execute: python baixar_modelo_piscadas.py')
        if not hasattr(cv2, 'face') or not hasattr(cv2.face, 'createFacemarkLBF'):
            raise RuntimeError('OpenCV sem FacemarkLBF. Instale a versão contrib compatível.')
        self.facemark = cv2.face.createFacemarkLBF()
        self.facemark.loadModel(str(model_path))

    def measure(self, frame, face):
        height, width = frame.shape[:2]
        x, y, w, h = (int(v) for v in face[:4])
        if min(w, h) < 80 or x < 0 or y < 0 or x+w > width or y+h > height:
            return None
        # A bounded face ROI avoids fitting on the whole camera image.
        margin = round(max(w, h) * 0.15)
        left, top = max(0, x-margin), max(0, y-margin)
        right, bottom = min(width, x+w+margin), min(height, y+h+margin)
        roi = frame[top:bottom, left:right]
        scale = min(1.0, 256 / max(roi.shape[:2]))
        if scale < 1:
            roi = cv2.resize(roi, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
        gray = cv2.cvtColor(roi, cv2.COLOR_BGR2GRAY)
        box = np.array([[round((x-left)*scale), round((y-top)*scale),
                         round(w*scale), round(h*scale)]], dtype=np.int32)
        try:
            ok, landmarks = self.facemark.fit(gray, box)
        except cv2.error:
            return None
        if not ok or len(landmarks) != 1:
            return None
        points = np.asarray(landmarks[0]).reshape(-1, 2)
        if points.shape != (68, 2) or not np.isfinite(points).all():
            return None
        eyes = points[36:48]
        if (eyes < 0).any() or (eyes[:, 0] >= gray.shape[1]).any() or (eyes[:, 1] >= gray.shape[0]).any():
            return None
        # Reject severely tilted or implausibly placed eyes. LBF has no confidence score.
        centers = [points[36:42].mean(axis=0), points[42:48].mean(axis=0)]
        separation = float(np.linalg.norm(centers[0] - centers[1]))
        if separation < w*scale*0.2 or abs(centers[0][1]-centers[1][1]) > separation*0.4:
            return None
        ratios = (eye_aspect_ratio(points[36:42]), eye_aspect_ratio(points[42:48]))
        return None if any(v is None for v in ratios) else ratios
