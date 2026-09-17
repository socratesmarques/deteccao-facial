import numpy as np
import recognition_worker as module
from configuracoes import CONFIG_PADRAO


def test_latest_result_replaces_old_result():
    worker = module.RecognitionWorker(CONFIG_PADRAO, np.empty((0, 128)), np.array([]))
    worker.publish({'value': 1})
    worker.publish({'value': 2})
    assert worker.take() == {'value': 2}
    assert worker.take() is None


def test_camera_failure_releases_resource(monkeypatch):
    class Camera:
        released = False
        def read(self):
            return False, None
        def release(self):
            self.released = True
    camera = Camera()
    monkeypatch.setattr(module, 'FaceEngine', lambda *args: object())
    monkeypatch.setattr(module, 'abrir_camera', lambda *args: camera)
    worker = module.RecognitionWorker(CONFIG_PADRAO, np.empty((0, 128)), np.array([]))
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert camera.released
    assert 'capturar' in worker.take()['error']
