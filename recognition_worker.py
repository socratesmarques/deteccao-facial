"""Camera/inference owner with a single replaceable result (no Qt event backlog)."""
from __future__ import annotations

import threading
import time

import cv2

from camera_utils import abrir_camera
from blink_challenge import BlinkChallenge
from eye_landmarks import EyeLandmarks
from face_engine import FaceEngine
from single_face import SingleFaceProcessor


class RecognitionWorker(threading.Thread):
    def __init__(self, config, profiles, names):
        super().__init__(daemon=True)
        self.config = dict(config)
        self.profiles, self.names = profiles.copy(), names.copy()
        self.stop_event = threading.Event()
        self.lock = threading.Lock()
        self.latest = None
        self.permit = None
        self.consumed_token = None
        self.reset_challenge = threading.Event()

    def publish(self, result):
        with self.lock:
            token = result.get('blink_token')
            self.permit = (token, result['captured']) if (
                token and token != self.consumed_token and not self.reset_challenge.is_set()
            ) else None
            self.latest = result

    def take(self):
        with self.lock:
            result, self.latest = self.latest, None
        return result

    def consume_permit(self, token):
        # The current worker state must still agree with the frame shown by Qt.
        with self.lock:
            if (self.stop_event.is_set() or self.permit is None or
                    self.permit[0] != token or time.monotonic() - self.permit[1] > 1.0):
                return False
            self.permit = None
            self.consumed_token = token
            self.reset_challenge.set()
            return True

    def invalidate_challenge(self):
        with self.lock:
            self.permit = None
            self.reset_challenge.set()

    def run(self):
        camera = None
        try:
            engine = FaceEngine(self.config['confianca_deteccao'])
            eyes = EyeLandmarks()
            challenge = BlinkChallenge(confirmations=self.config['frames_confirmacao'])
            authorized = set(self.config['pessoas_autorizadas'])
            processor = SingleFaceProcessor(engine, self.profiles, self.names, self.config)
            camera = abrir_camera(self.config['camera'], self.config['largura_camera'],
                                  self.config['altura_camera'], self.config['fps_camera'])
            if camera is None:
                raise RuntimeError('Não foi possível abrir a câmera.')
            while not self.stop_event.is_set():
                with self.lock:
                    if self.reset_challenge.is_set():
                        challenge.reset()
                        self.reset_challenge.clear()
                start = time.monotonic()
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError('Falha ao capturar imagem. Reinicie a câmera.')
                ratios = None
                def measure_before_recognition(image, selected):
                    nonlocal ratios
                    ratios = eyes.measure(image, selected)
                    return challenge.allow_recognition(ratios)
                face, name, score, fresh, generation = processor.process(
                    frame, time.monotonic(), before_recognition=measure_before_recognition)
                now = time.monotonic()
                eligible = face is not None and name.strip().lower() in authorized and name != 'Desconhecido'
                # Original unpainted pixels, one selected ROI only. Eye sampling is NOT
                # throttled by the SFace interval: blink transitions need every frame.
                token = challenge.update((generation, name) if eligible else None, fresh, ratios, now)
                if time.monotonic() - start > 1.0:
                    challenge.reset()
                    token = None
                prompt = challenge.prompt if eligible else ('Pessoa não autorizada ou não reconhecida'
                                                            if face is not None else 'Aguardando rosto selecionado...')
                if face is not None:
                    x, y, w, h = (int(v) for v in face[:4])
                    color = (0, 0, 255) if name == 'Desconhecido' else (0, 255, 0)
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                    cv2.putText(frame, f'{name} {score:.2f}', (x, max(20, y-10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
                self.publish(dict(frame=frame, name=name, fresh=fresh, visible=face is not None,
                                  generation=generation, captured=start, error=None,
                                  blink_token=token, blink_prompt=prompt,
                                  blink_diagnostic=challenge.diagnostic(ratios) + "\n" + eyes.status))
                self.stop_event.wait(max(0, 1 / self.config['fps_camera'] - (time.monotonic()-start)))
        except Exception as error:
            self.publish(dict(error=f'Erro na câmera/reconhecimento: {error}'))
        finally:
            if camera is not None:
                camera.release()

    def stop(self):
        self.stop_event.set()
        self.invalidate_challenge()
        self.join(timeout=2)
        return not self.is_alive()
