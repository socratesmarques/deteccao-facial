"""Experimental blink challenge. Not a presentation-attack detection guarantee."""
from __future__ import annotations

import math
import secrets


class BlinkChallenge:
    def __init__(self, confirmations=5, closed_threshold=0.20, open_threshold=0.25):
        self.confirmations = confirmations
        self.closed_threshold = closed_threshold
        self.open_threshold = open_threshold
        self.previous_target = None
        self.reset()

    def reset(self):
        # Keep previous_target across resets so consecutive challenges differ.
        self.key = None
        self.confirmed = 0
        self.target = None
        self.count = 0
        self.token = None
        self.started = None
        self.last_sample = None
        self.closed_at = None
        self.closed_samples = 0
        self.open_samples = 0
        self.armed = False
        self.completed_at = None
        self.prompt = 'Aguardando reconhecimento...'

    def update(self, key, fresh, ears, now):
        if key is None:
            self.reset()
            return None
        if self.key != key or (self.last_sample is not None and
                               (now <= self.last_sample or now - self.last_sample > 0.6)):
            self.reset()
            self.key = key
        self.last_sample = now
        if ears is None or len(ears) != 2 or not all(math.isfinite(v) and 0 <= v <= 0.8 for v in ears):
            self.reset()
            self.prompt = 'Olhos não visíveis. Olhe de frente e aproxime-se.'
            return None
        if self.target is None:
            if fresh:
                self.confirmed += 1
            self.prompt = f'Confirmando identidade... {self.confirmed}/{self.confirmations}'
            if self.confirmed < self.confirmations:
                return None
            self.target = secrets.choice([n for n in range(1, 6) if n != self.previous_target])
            self.previous_target = self.target
            self.token = secrets.token_urlsafe(24)
            self.started = now
            self.prompt = f'Pisque {self.target} vezes devagar: 0/{self.target}'
            return None  # never count an observation predating the prompt
        if now - self.started > 25 or (self.completed_at is not None and now - self.completed_at > 3):
            self.reset()
            self.prompt = 'Tempo esgotado. Preparando novo desafio...'
            return None

        opened = min(ears) >= self.open_threshold
        closed = max(ears) <= self.closed_threshold
        if self.completed_at is not None:
            # Require open eyes and a NEW recognition after the last blink.
            if not opened:
                self.reset()
                self.prompt = 'Mantenha os olhos abertos após a última piscada. Tente novamente.'
                return None
            self.prompt = 'Piscadas concluídas. Confirmando identidade novamente...'
            return self.token if fresh and now > self.completed_at else None

        if closed:
            self.open_samples = 0
            if self.armed:
                if self.closed_at is None:
                    self.closed_at = now
                self.closed_samples += 1
                if now - self.closed_at > 1.5:
                    self.reset()
                    self.prompt = 'Olhos fechados por muito tempo. Tente novamente.'
                    return None
        elif opened:
            self.open_samples += 1
            if self.open_samples >= 2:
                if self.closed_at is not None:
                    duration = now - self.closed_at
                    if self.closed_samples >= 2 and 0.08 <= duration <= 1.5:
                        self.count += 1
                    self.closed_at = None
                    self.closed_samples = 0
                self.armed = True
        else:
            # Hysteresis: uncertain/one-eye-only samples cannot complete a blink.
            self.open_samples = 0
            if self.closed_at is not None and now - self.closed_at > 1.5:
                self.reset()
                return None
        self.prompt = f'Pisque {self.target} vezes devagar: {self.count}/{self.target}'
        if self.count == self.target:
            self.completed_at = now
            self.prompt = 'Piscadas concluídas. Mantenha os olhos abertos.'
        return None
