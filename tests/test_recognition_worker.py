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
    monkeypatch.setattr(module, 'EyeLandmarks', lambda: object())
    monkeypatch.setattr(module, 'abrir_camera', lambda *args: camera)
    worker = module.RecognitionWorker(CONFIG_PADRAO, np.empty((0, 128)), np.array([]))
    worker.start()
    worker.join(timeout=2)
    assert not worker.is_alive()
    assert camera.released
    assert 'capturar' in worker.take()['error']


def test_permit_is_single_use_and_revoked_by_new_state():
    import time
    worker = module.RecognitionWorker(CONFIG_PADRAO, np.empty((0, 128)), np.array([]))
    worker.publish(dict(blink_token='once', captured=time.monotonic()))
    assert worker.consume_permit('wrong') is False
    assert worker.consume_permit('once') is True
    assert worker.consume_permit('once') is False
    worker.reset_challenge.clear()
    worker.publish(dict(blink_token='once', captured=time.monotonic()))
    assert worker.consume_permit('once') is False
    worker.publish(dict(blink_token='new', captured=time.monotonic()))
    worker.publish(dict(error='lost face'))
    assert worker.consume_permit('new') is False
    worker.publish(dict(blink_token='expired', captured=time.monotonic()-2))
    assert worker.consume_permit('expired') is False


def test_explicit_invalidation_prevents_delayed_permit():
    import time
    worker = module.RecognitionWorker(CONFIG_PADRAO, np.empty((0, 128)), np.array([]))
    worker.publish(dict(blink_token='once', captured=time.monotonic()))
    worker.invalidate_challenge()
    worker.publish(dict(blink_token='once', captured=time.monotonic()))
    assert worker.consume_permit('once') is False


def test_complete_pipeline_requires_blinks_and_revokes_after_disappearance(monkeypatch):
    from types import SimpleNamespace
    import blink_challenge
    clock = [0.0]
    monkeypatch.setattr(module, 'time', SimpleNamespace(monotonic=lambda: clock[0]))
    monkeypatch.setattr(blink_challenge.secrets, 'choice', lambda choices: choices[0])
    worker = module.RecognitionWorker(dict(CONFIG_PADRAO, pessoas_autorizadas=['ana']),
                                      np.ones((1, 128)), np.array(['ana']))
    # Identity + guided calibration + low-FPS one-frame blink + recheck + loss.
    sequence = [(0.3, 0.3)]*10 + [(0.1, 0.1)]*3 + [(0.3, 0.3)]*2 + [(0.1, 0.1)] + [(0.3, 0.3)]*3 + [None]
    index = [-1]
    released = []
    class Camera:
        def read(self):
            index[0] += 1
            clock[0] += 0.2
            if index[0] == len(sequence)-1:
                worker.stop_event.set()
            return True, np.zeros((200, 200, 3), dtype=np.uint8)
        def release(self):
            released.append(True)
    class Eyes:
        status = 'OK'
        def measure(self, frame, face):
            return sequence[index[0]]
    class Processor:
        def __init__(self, *args):
            pass
        def process(self, frame, now, before_recognition=None):
            face = None if sequence[index[0]] is None else np.array([10, 10, 100, 100])
            fresh = before_recognition(frame, face) if face is not None else False
            return face, 'ana', 0.9, fresh, 1
    monkeypatch.setattr(module, 'abrir_camera', lambda *args: Camera())
    monkeypatch.setattr(module, 'FaceEngine', lambda *args: object())
    monkeypatch.setattr(module, 'EyeLandmarks', Eyes)
    monkeypatch.setattr(module, 'SingleFaceProcessor', Processor)
    results = []
    original_publish = worker.publish
    def publish(result):
        results.append(result)
        original_publish(result)
    monkeypatch.setattr(worker, 'publish', publish)
    worker.run()
    assert not any(r['blink_token'] for r in results[:-2])
    assert results[-2]['blink_token']
    assert results[-1]['blink_token'] is None
    assert worker.permit is None
    assert released == [True]
