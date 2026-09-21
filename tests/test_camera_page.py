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
        def stop(self):
            return True
    worker = Worker()
    page.worker = worker
    confirmed = []
    monkeypatch.setattr(page, 'verificar_acesso', lambda name, pose=None: confirmed.append(name))
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
    assert confirmed == ['ana']
    page.close()
