import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')

import time
import numpy as np
from PySide6.QtWidgets import QApplication
from interface.paginas.pagina_camera import PaginaCamera


def test_only_fresh_visible_results_can_confirm(monkeypatch):
    app = QApplication.instance() or QApplication([])
    page = PaginaCamera()
    class Worker:
        result = None
        def take(self):
            result, self.result = self.result, None
            return result
        def invalidate_challenge(self):
            pass
        def stop(self):
            return True
    worker = Worker()
    page.worker = worker
    confirmed = []
    monkeypatch.setattr(page, 'verificar_acesso', lambda name, token: confirmed.append((name, token)))
    monkeypatch.setattr(page, '_mostrar_frame', lambda frame: None)
    base = dict(frame=np.zeros((100, 100, 3), dtype=np.uint8), name='ana',
                fresh=True, visible=True, generation=1, error=None)
    worker.result = dict(base, captured=time.monotonic())
    page.atualizar_camera()
    worker.result = dict(base, fresh=False, captured=time.monotonic())
    page.atualizar_camera()
    worker.result = dict(base, visible=False, captured=time.monotonic())
    page.atualizar_camera()
    worker.result = dict(base, captured=time.monotonic()-2)
    page.atualizar_camera()
    assert confirmed == [('ana', None)]
    page.close()


def test_access_cannot_open_without_blink_permit_or_reuse_it(monkeypatch):
    app = QApplication.instance() or QApplication([])
    page = PaginaCamera()
    page.config['pessoas_autorizadas'] = ['ana']
    page.ultimo_acesso = float('-inf')
    class Worker:
        used = False
        def consume_permit(self, token):
            if token != 'valid' or self.used:
                return False
            self.used = True
            return True
        def stop(self):
            return True
    page.worker = Worker()
    opened = []
    class Thread:
        def __init__(self, **kwargs):
            pass
        def start(self):
            opened.append(True)
    monkeypatch.setattr('interface.paginas.pagina_camera.threading.Thread', Thread)
    page.verificar_acesso('ana')
    page.verificar_acesso('ana', 'invalid')
    page.verificar_acesso('outsider', 'valid')
    assert not opened
    page.verificar_acesso('ana', 'valid')
    assert len(opened) == 1
    page.abrindo_porta = False
    page.verificar_acesso('ana', 'valid')
    assert len(opened) == 1
    page.close()
