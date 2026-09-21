"""Anti-spoofing passivo com os dois modelos MiniFASNet, executados pelo OpenCV.

O recorte segue src/generate_patches.py do Silent-Face-Anti-Spoofing.
Copyright 2020 Minivision. Apache-2.0: third_party/Silent-Face-Anti-Spoofing-LICENSE.txt.
Adaptações FaceAI: validações, ONNX, ensemble conservador e janela temporal.
"""
from collections import deque
import hashlib
import json
from pathlib import Path

import cv2
import numpy as np

from app_paths import MODELS_DIR


MODEL_FILES = [('2.7_80x80_MiniFASNetV2.onnx', 2.7), ('4_0_0_80x80_MiniFASNetV1SE.onnx', 4.0)]


def crop_patch(frame, box, scale):
    """Recorte com contexto, BGR preservado; coordenadas inclusivas do upstream."""
    if not isinstance(frame, np.ndarray) or frame.dtype != np.uint8 or frame.ndim != 3 or frame.shape[2] != 3:
        raise ValueError('Imagem BGR inválida para anti-spoofing.')
    coords = np.asarray(box[:4], dtype=float)
    if coords.shape != (4,) or not np.all(np.isfinite(coords)):
        raise ValueError('Rosto inválido para anti-spoofing.')
    x, y, w, h = coords
    src_h, src_w = frame.shape[:2]
    if min(w, h) < 80:
        raise ValueError('Aproxime o rosto da câmera.')
    if x < 0 or y < 0 or x+w > src_w or y+h > src_h:
        raise ValueError('Centralize o rosto inteiro na câmera.')
    scale = min((src_h-1)/h, (src_w-1)/w, scale)
    if scale < 1.5:
        raise ValueError('Afaste um pouco o rosto para incluir contexto na imagem.')
    new_w, new_h = w*scale, h*scale
    cx, cy = x+w/2, y+h/2
    left, top, right, bottom = cx-new_w/2, cy-new_h/2, cx+new_w/2, cy+new_h/2
    if left < 0:
        right -= left; left = 0
    if top < 0:
        bottom -= top; top = 0
    if right > src_w-1:
        left -= right-src_w+1; right = src_w-1
    if bottom > src_h-1:
        top -= bottom-src_h+1; bottom = src_h-1
    patch = frame[int(top):int(bottom)+1, int(left):int(right)+1]
    if patch.size == 0:
        raise ValueError('Recorte vazio para anti-spoofing.')
    return cv2.resize(patch, (80,80), interpolation=cv2.INTER_LINEAR)


def probabilities(logits):
    values = np.asarray(logits, dtype=np.float64).reshape(-1)
    if values.shape != (3,) or not np.all(np.isfinite(values)):
        raise RuntimeError('Saída inválida do modelo anti-spoofing.')
    exp = np.exp(values - values.max())
    return exp/exp.sum()


class AntiSpoofEngine:
    def __init__(self, threshold=0.8, model_dir=None):
        self.threshold = float(threshold)
        if not .8 <= self.threshold <= .99:
            raise ValueError('Limiar anti-spoofing fora do intervalo permitido.')
        directory = Path(model_dir) if model_dir is not None else MODELS_DIR/'antispoof'
        try:
            manifest = json.loads((directory/'manifest.json').read_text())
            entries = {entry['file']:entry for entry in manifest['models']}
            self.nets = []
            for filename, scale in MODEL_FILES:
                path = directory/filename
                if hashlib.sha256(path.read_bytes()).hexdigest() != entries[filename]['sha256']:
                    raise RuntimeError(f'Modelo anti-spoofing corrompido: {filename}')
                net = cv2.dnn.readNetFromONNX(str(path))
                net.setPreferableBackend(cv2.dnn.DNN_BACKEND_OPENCV)
                net.setPreferableTarget(cv2.dnn.DNN_TARGET_CPU)
                self.nets.append((net, scale))
        except (OSError, ValueError, KeyError, TypeError, cv2.error) as error:
            raise RuntimeError(f'Não foi possível carregar os modelos anti-spoofing: {error}') from error

    def analyze(self, frame, face):
        try:
            patches = [crop_patch(frame, face, scale) for _,scale in self.nets]
        except ValueError as error:
            return dict(state='uncertain', score=None, reason=str(error))
        probs = []
        for (net, _), patch in zip(self.nets, patches):
            # Atenção: o código original usa BGR em 0..255, SEM divisão por 255.
            blob = cv2.dnn.blobFromImage(patch, scalefactor=1.0, size=(80,80), swapRB=False, crop=False)
            net.setInput(blob)
            probs.append(probabilities(net.forward()))
        real = [float(p[1]) for p in probs]
        score = min(real)
        if all(int(np.argmax(p)) == 1 and p[1] >= self.threshold for p in probs):
            state, reason = 'live', 'Os dois modelos aprovam a amostra.'
        elif any(int(np.argmax(p)) != 1 and max(p[0],p[2]) >= self.threshold for p in probs):
            state, reason = 'spoof', 'Suspeita de foto/tela ou outra apresentação artificial.'
        else:
            state, reason = 'uncertain', 'Análise inconclusiva. Ajuste a iluminação e o enquadramento.'
        return dict(state=state, score=score, scores=real, reason=reason)


class AntiSpoofWindow:
    REQUIRED = 5
    MIN_INTERVAL = .15
    MAX_GAP = 2.5

    def __init__(self):
        self.reset()

    def reset(self):
        self.samples = deque(maxlen=self.REQUIRED)
        self.current = dict(state='pending', count=0, score=None, reason='Aguardando análise anti-spoofing.',
                            first_observation=0, last_observation=0, sampled_at=None)

    def add(self, prediction, observation, now):
        state = prediction.get('state', 'error')
        if state != 'live':
            self.reset()
            self.current.update(prediction, count=0, first_observation=observation,
                                last_observation=observation, sampled_at=now)
            return
        score = prediction.get('score')
        if score is None or not np.isfinite(score) or not .8 <= score <= 1:
            self.add(dict(state='error', score=None, reason='Evidência anti-spoofing inválida.'), observation, now)
            return
        if self.samples:
            gap = now-self.samples[-1][1]
            if gap < 0 or gap > self.MAX_GAP:
                self.reset()
            elif gap < self.MIN_INTERVAL:
                return
        self.samples.append((observation, now, score))
        self.current = dict(state='live' if len(self.samples) == self.REQUIRED else 'pending',
                            count=len(self.samples), score=min(s[2] for s in self.samples),
                            first_observation=self.samples[0][0], last_observation=observation,
                            sampled_at=now, reason='Cinco análises aprovadas.' if len(self.samples)==self.REQUIRED else 'Analisando presença real.')

    def snapshot(self):
        return dict(self.current)
