from __future__ import annotations

import sys

import cv2


def abrir_camera(dispositivo, largura: int, altura: int, fps: int):
    """Abre a câmera com baixa latência e fallback entre backends."""
    fonte = int(dispositivo) if str(dispositivo).isdigit() else dispositivo
    backends = [cv2.CAP_V4L2, cv2.CAP_ANY] if sys.platform.startswith("linux") else [cv2.CAP_ANY]

    for backend in backends:
        camera = cv2.VideoCapture(fonte, backend)
        if not camera.isOpened():
            camera.release()
            continue
        camera.set(cv2.CAP_PROP_FRAME_WIDTH, largura)
        camera.set(cv2.CAP_PROP_FRAME_HEIGHT, altura)
        camera.set(cv2.CAP_PROP_FPS, fps)
        camera.set(cv2.CAP_PROP_BUFFERSIZE, 1)
        return camera
    return None
