"""Camera/inference owner with a single replaceable result (no Qt event backlog)."""
from __future__ import annotations

import threading
import time

from camera_utils import abrir_camera
from face_engine import FaceEngine
from single_face import SingleFaceProcessor
from anti_spoof import AntiSpoofEngine


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
            anti, anti_error = None, None
            try:
                anti = AntiSpoofEngine(self.config.get('limiar_antispoof', .8))
            except Exception as error:
                anti_error = str(error)
            processor = SingleFaceProcessor(engine, self.profiles, self.names, self.config, anti, anti_error)
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
                self.publish(dict(frame=frame, name=name, fresh=fresh, visible=face is not None,
                                  liberado=liberado, generation=generation,
                                  observations=processor.confirmations, encounter=processor.target.encounter,
                                  variation=processor.variation.snapshot(),
                                  antispoof=processor.anti_spoof_window.snapshot(),
                                  face_box=tuple(float(v) for v in face[:4]) if face is not None else None,
                                  captured=start, error=None))
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
