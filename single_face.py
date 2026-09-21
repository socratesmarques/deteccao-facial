"""One spatial target at a time; never reuse identity across missing detections."""
from __future__ import annotations

import numpy as np
from frame_variation import FrameVariation
from anti_spoof import AntiSpoofWindow


def iou(a, b):
    x = max(a[0], b[0]); y = max(a[1], b[1])
    right = min(a[0] + a[2], b[0] + b[2])
    bottom = min(a[1] + a[3], b[1] + b[3])
    intersection = max(0, right - x) * max(0, bottom - y)
    return intersection / max(1, a[2] * a[3] + b[2] * b[3] - intersection)


class SingleFace:
    def __init__(self, absence_seconds=0.7):
        self.box = None
        self.missing_since = None
        self.absence_seconds = absence_seconds
        self.generation = 0
        self.encounter = 0

    def select(self, faces, now):
        if self.box is None:
            if len(faces) == 0:
                return None
            face = max(faces, key=lambda f: float(f[2] * f[3]))
            self.box = np.array(face[:4], copy=True)
            self.generation += 1
            self.encounter += 1
            return face
        matches = sorted(((iou(self.box, f), i) for i, f in enumerate(faces)), reverse=True)
        # Ambiguous overlapping faces: hold the target, with no recognition/rendering.
        if matches and matches[0][0] >= 0.3 and (
            len(matches) == 1 or matches[0][0] - matches[1][0] >= 0.15
        ):
            face = faces[matches[0][1]]
            if self.missing_since is not None:
                self.generation += 1  # invalidate all earlier identity/confirmation
            self.box = np.array(face[:4], copy=True)
            self.missing_since = None
            return face
        self.generation += 1
        if matches and matches[0][0] >= 0.3:
            self.missing_since = None  # ambiguous, but the target area is occupied
            return None
        if self.missing_since is None:
            self.missing_since = now
        if now - self.missing_since >= self.absence_seconds:
            self.box = None
            self.missing_since = None
        return None  # next target is acquired only on a subsequent frame


class SingleFaceProcessor:
    def __init__(self, engine, profiles, names, config, anti_spoof=None, anti_spoof_error=None):
        self.engine, self.profiles, self.names, self.config = engine, profiles, names, config
        self.target = SingleFace()
        self.last_recognition = float('-inf')
        self.generation = -1
        self.name, self.score = 'Desconhecido', 0.0
        self.frames = 0
        self.evidence_epoch = 0
        self.confirmations = 0
        self.variation = FrameVariation()
        self.anti_spoof = anti_spoof
        self.anti_spoof_error = anti_spoof_error
        self.anti_spoof_window = AntiSpoofWindow()

    def process(self, frame, now):
        self.frames += 1
        faces = self.engine.detectar(frame, largura_maxima=self.config['largura_deteccao'])
        face = self.target.select(faces, now)
        changed = self.generation != self.target.generation
        self.generation = self.target.generation
        if changed or face is None:
            self.evidence_epoch += 1
            self.name, self.score = 'Desconhecido', 0.0
            self.last_recognition = float('-inf')
            self.confirmations = 0
            self.variation.reset()
            self.anti_spoof_window.reset()
        fresh = False
        if face is not None and (changed or (
            now - self.last_recognition >= self.config['intervalo_reconhecimento']
            and self.frames % self.config['processar_a_cada_frames'] == 0
        )):
            previous_name = self.name
            # At most one SFace inference, independently of the crowd size.
            if len(self.profiles):
                vector = self.engine.embedding(frame, face)
                self.name, self.score = self.engine.reconhecer(
                    vector, self.profiles, self.names, self.config['limiar_reconhecimento'])
            if self.name != previous_name:
                self.evidence_epoch += 1
                self.confirmations = 0
                self.variation.reset()
                self.anti_spoof_window.reset()
            self.confirmations += 1
            if self.name != 'Desconhecido':
                self.variation.observe(frame, face, self.confirmations, now)
                if self.name.strip().lower() in self.config['pessoas_autorizadas']:
                    if self.anti_spoof is None:
                        prediction = dict(state='error', score=None, reason=self.anti_spoof_error or 'Modelos anti-spoofing indisponíveis.')
                    else:
                        try:
                            prediction = self.anti_spoof.analyze(frame, face)
                        except Exception as error:
                            prediction = dict(state='error', score=None, reason=f'Falha na análise anti-spoofing: {error}')
                    self.anti_spoof_window.add(prediction, self.confirmations, now)
                else:
                    self.anti_spoof_window.reset()
            else:
                self.variation.reset()
                self.anti_spoof_window.reset()
            self.last_recognition = now
            fresh = True
        return face, self.name, self.score, fresh, self.evidence_epoch
