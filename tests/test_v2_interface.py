"""Regressões de navegação, exclusividade da câmera e feedback do relé."""
import os
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import time
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication
import app_paths
import configuracoes
import access_logger
import perfil_store
from interface.paginas.pagina_camera import PaginaCamera
from interface.janela_principal import JanelaPrincipal
from interface.paginas.pagina_cadastro import PaginaCadastro


@pytest.fixture
def app(tmp_path, monkeypatch):
    application = QApplication.instance() or QApplication([])
    monkeypatch.setattr(app_paths, "PRIVATE_DATA_DIR", tmp_path)
    monkeypatch.setattr(access_logger, "PRIVATE_DATA_DIR", tmp_path)
    monkeypatch.setattr(configuracoes, "CONFIG_FILE", tmp_path / "config.json")
    monkeypatch.setattr(perfil_store.PerfilStore, "carregar",
                        lambda self: (np.empty((0, 128), dtype=np.float32), np.array([], dtype=str)))
    return application


@pytest.fixture
def window(app, monkeypatch):
    monkeypatch.setattr(PaginaCamera, "iniciar_camera", lambda self: None)
    monkeypatch.setattr(JanelaPrincipal, "_exigir_admin", lambda self: True)
    window = JanelaPrincipal()
    yield window
    window.close()


@pytest.mark.parametrize("size", [(800, 480), (1024, 768), (480, 800)])
def test_display_fits_and_settings_scroll(window, app, size):
    # Portrait displays narrower than the documented minimum use the minimum width.
    window.resize(*size)
    window.show()
    app.processEvents()
    assert window.width() == max(640, size[0])
    page = window.pagina_camera
    assert page.camera_label.height() > window.height() * 0.55
    assert page.camera_label.width() <= window.width()
    window.abrir_configuracoes()
    app.processEvents()
    assert window.botao_voltar.isVisible()
    container = window._containers['pagina_config']
    assert container.widgetResizable()
    assert container.horizontalScrollBar().maximum() == 0
    window.abrir_camera()
    assert window.paginas.currentWidget() is page
    assert not window.botao_voltar.isVisible()


def test_admin_lazy_load_and_camera_owner(window, monkeypatch):
    assert window.pagina_cadastro is None
    monkeypatch.setattr(window.pagina_camera, "parar_camera", lambda: False)
    window.abrir_cadastro()
    assert window.pagina_cadastro is None
    monkeypatch.setattr(window.pagina_camera, "parar_camera", lambda: True)
    window.abrir_cadastro()
    assert window.pagina_cadastro.engine is None
    window.abrir_camera()
    assert not window.pagina_cadastro.cadastrando


def test_error_feedback_and_stale_frame(app):
    page = PaginaCamera()
    page.logger.registrar = lambda *args: None
    page.controle_acesso.ultimo_erro = "GPIO indisponível"
    page._mostrar_resultado_porta(False, "Pessoa Exemplo")
    assert "ERRO NO RELÉ" in page.status_acesso.text()
    class Worker:
        def take(self):
            return dict(error=None, captured=time.monotonic()-2)
        def stop(self):
            return True
    page.worker = Worker()
    page._mostrar_resultado_porta(True, "Pessoa Exemplo")
    assert "LIBERADO" in page.status_acesso.text()
    page.atualizar_camera()
    assert "LIBERADO" not in page.status_acesso.text()
    page.close()


def test_registration_releases_models_and_saves_synthetic_profile(app):
    page = PaginaCadastro(lambda: True)
    page.engine = object()
    page.embeddings = [np.ones(128, dtype=np.float32)]
    page.nome_atual = "pessoa exemplo"
    saved = []
    page.store.salvar_perfil = lambda name, profile: saved.append((name, profile))
    page.finalizar_cadastro()
    assert page.engine is None
    assert saved[0][0] == "pessoa exemplo"
    assert np.linalg.norm(saved[0][1]) == pytest.approx(1.0)
    assert page.botao_iniciar.isEnabled()
    page.close()


def test_video_preserves_aspect_ratio_after_resize(app):
    from PySide6.QtGui import QColor, QPixmap
    from interface.camera_view import CameraView
    view = CameraView()
    frame = QPixmap(640, 480)
    frame.fill(QColor('#dd1122'))
    view.resize(800, 400)
    view.setPixmap(frame)
    view.show(); app.processEvents()
    pixels = view.grab().toImage()
    assert pixels.pixelColor(10, 200).name() == '#050a10'
    assert pixels.pixelColor(150, 200).name() == '#dd1122'
    assert pixels.pixelColor(650, 200).name() == '#dd1122'
    view.resize(400, 600); app.processEvents()
    pixels = view.grab().toImage()
    assert pixels.pixelColor(200, 80).name() == '#050a10'
    assert pixels.pixelColor(200, 160).name() == '#dd1122'
    view.close()
