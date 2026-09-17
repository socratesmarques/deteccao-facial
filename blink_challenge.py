"""Experimental calibrated blink challenge; not robust anti-spoofing."""
from __future__ import annotations

import math
import secrets
from statistics import median


def valid_ears(ears):
    return ears is not None and len(ears) == 2 and all(math.isfinite(v) and 0 <= v <= 0.8 for v in ears)


class BlinkChallenge:
    def __init__(self, confirmations=5):
        self.confirmations = confirmations
        self.previous_target = None
        self.reason = ''
        self.reset()

    def reset(self, reason=''):
        self.key = None
        self.confirmed = 0
        self.phase = 'identity'
        self.target = None
        self.count = 0
        self.token = None
        self.started = None
        self.last_sample = None
        self.intervals = []
        self.samples = []
        self.baseline = None
        self.closed_thresholds = None
        self.open_thresholds = None
        self.closed_at = None
        self.closed_samples = 0
        self.required_closed_samples = 2
        self.open_samples = 0
        self.armed = False
        self.completed_at = None
        self.eye_state = 'aguardando'
        if reason:
            self.reason = reason
        self.prompt = reason or 'Aguardando reconhecimento...'

    def allow_recognition(self, ears):
        # Closing the eyes changes the SFace embedding. Defer that inference, then
        # require a new identity observation after reopening; never accept cache.
        if not valid_ears(ears):
            return False
        if self.phase == 'calibrate_closed':
            return False
        if self.open_thresholds is not None:
            return all(v >= threshold for v, threshold in zip(ears, self.open_thresholds))
        return True

    def _sample_calibration(self, ears, now, minimum, span):
        self.samples.append((now, tuple(ears)))
        self.samples = [sample for sample in self.samples[-120:] if now - sample[0] <= 1.2]
        return len(self.samples) >= minimum and now - self.samples[0][0] >= span

    def _medians(self):
        return tuple(median(sample[1][i] for sample in self.samples) for i in (0, 1))

    def _calibrate(self, ears, now):
        if self.phase == 'calibrate_open':
            self.prompt = 'Calibração: mantenha os olhos abertos normalmente, sem arregalar.'
            if self._sample_calibration(ears, now, 5, 0.6):
                baseline = self._medians()
                # Reject unstable open reference instead of adapting to arbitrary noise.
                stable = all(b >= 0.12 and max(abs(s[1][i]-b) for s in self.samples) <= b*0.20
                             for i, b in enumerate(baseline))
                if stable:
                    self.baseline = baseline
                    self.samples = []
                    self.phase = 'calibrate_closed'
                    self.prompt = 'Calibração: feche os dois olhos por cerca de 1 segundo e reabra.'
                else:
                    self.samples = self.samples[-1:]
            return
        if self.phase == 'calibrate_closed':
            self.prompt = 'Calibração: feche os dois olhos por cerca de 1 segundo e reabra.'
            # Require a measured drop on BOTH eyes. A static reference cannot calibrate.
            if all(b-v >= max(0.025, b*0.20) for b, v in zip(self.baseline, ears)):
                if self._sample_calibration(ears, now, 3, 0.25):
                    closed = self._medians()
                    self.closed_thresholds = tuple(c + (b-c)*0.35 for b, c in zip(self.baseline, closed))
                    self.open_thresholds = tuple(c + (b-c)*0.70 for b, c in zip(self.baseline, closed))
                    self.phase = 'reopen'
                    self.samples = []
                    self.open_samples = 0
                    self.prompt = 'Calibração concluída. Abra os olhos e aguarde o número de piscadas.'
            else:
                self.samples = []
            return
        if self.phase == 'reopen':
            self.open_samples = self.open_samples + 1 if self.allow_recognition(ears) else 0
            self.prompt = 'Abra os olhos e aguarde o número de piscadas.'
            if self.open_samples >= 2:
                self.target = secrets.choice([n for n in range(1, 6) if n != self.previous_target])
                self.previous_target = self.target
                self.token = secrets.token_urlsafe(24)
                self.started = now
                self.phase = 'challenge'
                self.armed = True
                self.prompt = f'Pisque {self.target} vezes: 0/{self.target}'

    def update(self, key, fresh, ears, now):
        if key is None:
            self.reset('Rosto ausente ou sem autorização; desafio reiniciado.')
            return None
        if self.key != key:
            self.reset('Identidade/alvo mudou; desafio reiniciado.' if self.key is not None else '')
            self.key = key
        if self.last_sample is not None:
            delta = now - self.last_sample
            if delta <= 0 or delta > 0.6:
                self.reset('Intervalo entre quadros muito grande; desafio reiniciado.')
                self.key = key
            else:
                self.intervals = (self.intervals + [delta])[-10:]
        self.last_sample = now
        if not valid_ears(ears):
            self.reset('Leitura dos olhos inválida; aproxime-se e olhe de frente.')
            return None
        self.eye_state = 'calibrando'
        if self.phase == 'identity':
            if fresh:
                self.confirmed += 1
            self.prompt = f'Confirmando identidade... {self.confirmed}/{self.confirmations}'
            if self.confirmed >= self.confirmations:
                self.phase = 'calibrate_open'
                self.started = now
                self.prompt = 'Calibração: mantenha os olhos abertos normalmente, sem arregalar.'
            return None
        if self.phase != 'challenge':
            if now - self.started > 20:
                self.reset('Calibração sem contraste suficiente ou incompleta. Verifique a leitura dos olhos.')
            else:
                self._calibrate(ears, now)
            return None
        if now - self.started > 25 or (self.completed_at is not None and now - self.completed_at > 3):
            self.reset('Tempo esgotado; desafio reiniciado.')
            return None

        opened = all(v >= t for v, t in zip(ears, self.open_thresholds))
        closed = all(v <= t for v, t in zip(ears, self.closed_thresholds))
        self.eye_state = 'abertos' if opened else 'fechados' if closed else 'intermediários'
        if self.completed_at is not None:
            if not opened:
                self.reset('Mantenha os olhos abertos após a última piscada; tente novamente.')
                return None
            self.prompt = 'Piscadas concluídas. Confirmando identidade novamente...'
            return self.token if fresh and now > self.completed_at else None

        if closed:
            self.open_samples = 0
            if self.armed:
                if self.closed_at is None:
                    self.closed_at = now
                    # At <=~8 FPS a real blink may occupy one frame. High sampling
                    # rates still need two closed observations to reject spikes.
                    self.required_closed_samples = 1 if (len(self.intervals) >= 3 and
                                                         median(self.intervals) >= 0.12) else 2
                self.closed_samples += 1
        elif opened:
            self.open_samples += 1
            if self.open_samples >= 2:
                if self.closed_at is not None:
                    duration = now - self.closed_at
                    if self.closed_samples >= self.required_closed_samples and 0.06 <= duration <= 1.5:
                        self.count += 1
                    else:
                        self.reason = 'Fechamento curto demais ou com poucas amostras; piscada descartada.'
                    self.closed_at = None
                    self.closed_samples = 0
                self.armed = True
        else:
            self.open_samples = 0
        if self.closed_at is not None and now - self.closed_at > 1.5:
            self.reset('Olhos fechados por muito tempo; desafio reiniciado.')
            return None
        self.prompt = f'Pisque {self.target} vezes: {self.count}/{self.target}'
        if self.count == self.target:
            self.completed_at = now
            self.prompt = 'Piscadas concluídas. Mantenha os olhos abertos.'
        return None

    def diagnostic(self, ears):
        values = 'sem leitura' if not valid_ears(ears) else f'EAR E/D: {ears[0]:.3f}/{ears[1]:.3f}'
        limits = '' if self.closed_thresholds is None else (
            f' | fechado ≤ {self.closed_thresholds[0]:.3f}/{self.closed_thresholds[1]:.3f}'
            f' | aberto ≥ {self.open_thresholds[0]:.3f}/{self.open_thresholds[1]:.3f}')
        rate = f' | amostras: {1/median(self.intervals):.1f}/s' if self.intervals else ''
        return f'Olhos: {self.eye_state} | {values}{limits}{rate}\nÚltimo aviso: {self.reason or "nenhum"}'
