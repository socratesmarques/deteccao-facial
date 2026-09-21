"""Regra de variação em cinco amostras. NÃO é um detector de vivacidade."""
from collections import deque

import cv2
import numpy as np


class FrameVariation:
    FRAMES = 5
    MIN_INTERVAL = 0.15
    MAX_GAP = 2.5
    MEAN_DIFFERENCE = 4.0
    PIXEL_DIFFERENCE = 10.0
    CHANGED_FRACTION = 0.08

    def __init__(self):
        self.samples = deque(maxlen=self.FRAMES)
        self._cached = None

    def reset(self):
        self.samples.clear()
        self._cached = None

    @staticmethod
    def signature(frame, face):
        if frame is None or face is None or len(face) < 4 or frame.size == 0:
            return None
        box = np.asarray(face[:4], dtype=float)
        if not np.all(np.isfinite(box)):
            return None
        x, y, w, h = box
        if w < 24 or h < 24:
            return None
        # Exclui as bordas da caixa para reduzir a influência do fundo.
        x0, y0 = max(0, int(x + .1*w)), max(0, int(y + .1*h))
        x1 = min(frame.shape[1], int(x + .9*w))
        y1 = min(frame.shape[0], int(y + .9*h))
        if x1-x0 < 16 or y1-y0 < 16:
            return None
        region = frame[y0:y1, x0:x1]
        gray = cv2.cvtColor(region, cv2.COLOR_BGR2GRAY) if region.ndim == 3 else region
        gray = cv2.resize(gray, (64, 64), interpolation=cv2.INTER_AREA)
        gray = cv2.GaussianBlur(gray, (5, 5), 0).astype(np.float32)
        # Uma mudança uniforme de brilho, sozinha, não conta como variação.
        return gray - float(gray.mean())

    def observe(self, frame, face, observation, now):
        signature = self.signature(frame, face)
        if signature is None:
            self.reset()
            return
        if self.samples:
            gap = now - self.samples[-1][1]
            if gap < 0 or gap > self.MAX_GAP:
                self.reset()
            elif gap < self.MIN_INTERVAL:
                return  # Não preencher cinco amostras em um único instante.
        self.samples.append((observation, now, signature))
        self._cached = None

    def snapshot(self):
        if self._cached is not None:
            return dict(self._cached)
        different = False
        # Basta existir um par visualmente diferente entre as cinco amostras.
        for index, (_, _, a) in enumerate(self.samples):
            for _, _, b in list(self.samples)[index+1:]:
                delta = np.abs(a-b)
                if float(delta.mean()) >= self.MEAN_DIFFERENCE and float(np.mean(delta >= self.PIXEL_DIFFERENCE)) >= self.CHANGED_FRACTION:
                    different = True
                    break
            if different:
                break
        self._cached = dict(count=len(self.samples), different=different,
                    first_observation=self.samples[0][0] if self.samples else 0,
                    last_observation=self.samples[-1][0] if self.samples else 0,
                    sampled_at=self.samples[-1][1] if self.samples else None)
        return dict(self._cached)
