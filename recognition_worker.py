"""Camera/inference owner with a single replaceable result (no Qt event backlog)."""
from __future__ import annotations

import threading
import time

import cv2

from camera_utils import abrir_camera
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
        self.autorizados = {
            str(nome).strip().lower() for nome in self.config.get('pessoas_autorizadas', [])
        }

    def publish(self, result):
        with self.lock:
            self.latest = result

    def take(self):
        with self.lock:
            result, self.latest = self.latest, None
        return result

    def run(self):
        camera = None
        try:
            engine = FaceEngine(self.config['confianca_deteccao'])
            processor = SingleFaceProcessor(engine, self.profiles, self.names, self.config)
            camera = abrir_camera(self.config['camera'], self.config['largura_camera'],
                                  self.config['altura_camera'], self.config['fps_camera'])
            if camera is None:
                raise RuntimeError('Não foi possível abrir a câmera.')
            while not self.stop_event.is_set():
                start = time.monotonic()
                ok, frame = camera.read()
                if not ok:
                    raise RuntimeError('Falha ao capturar imagem. Reinicie a câmera.')
                face, name, score, fresh, generation = processor.process(frame, time.monotonic())
                liberado = name != 'Desconhecido' and name.strip().lower() in self.autorizados
                if face is not None:
                    x, y, w, h = (int(v) for v in face[:4])
                    color = (0, 180, 0) if liberado else (0, 0, 255)
                    situacao = 'LIBERADO' if liberado else 'BLOQUEADO'
                    cv2.rectangle(frame, (x, y), (x+w, y+h), color, 2)
                    cv2.putText(frame, f'{name} - {situacao}', (x, max(20, y-10)),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.65, color, 2)
                self.publish(dict(frame=frame, name=name, fresh=fresh, visible=face is not None,
                                  liberado=liberado, generation=generation, captured=start, error=None))
                self.stop_event.wait(max(0, 1 / self.config['fps_camera'] - (time.monotonic()-start)))
        except Exception as error:
            self.publish(dict(error=f'Erro na câmera/reconhecimento: {error}'))
        finally:
            if camera is not None:
                camera.release()

    def stop(self):
        self.stop_event.set()
        self.join(timeout=2)
        return not self.is_alive()
