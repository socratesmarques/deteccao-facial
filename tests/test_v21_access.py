import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication, QDialog
import app_paths
import access_logger
import configuracoes
import perfil_store
from admin_auth import AdminAuth
from interface.admin_dialog import AdminDialog
from interface.janela_principal import JanelaPrincipal
from interface.paginas.pagina_camera import PaginaCamera
from interface.paginas.pagina_cadastro import PaginaCadastro
from interface.paginas.pagina_configuracoes import PaginaConfiguracoes
from interface.paginas.pagina_pessoas import PaginaPessoas


@pytest.fixture
def app(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(app_paths, 'PRIVATE_DATA_DIR', tmp_path)
    monkeypatch.setattr(access_logger, 'PRIVATE_DATA_DIR', tmp_path)
    monkeypatch.setattr(configuracoes, 'CONFIG_FILE', tmp_path/'config.json')
    monkeypatch.setattr(perfil_store.PerfilStore, 'carregar',
                        lambda self: (np.empty((0,128)), np.array([], dtype=str)))
    return app


def test_no_relay_authorizes_without_gpio_or_pose(app, monkeypatch):
    page = PaginaCamera()
    # These tests isolate prior behavior; model rejection is covered by test_anti_spoof.
    page.antispoof_atual = dict(state='live', count=5, score=.99, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    page.variacao_atual = dict(count=5, different=True, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    page.config.update(pessoas_autorizadas=['pessoa exemplo'], rele_ativo=False, frames_confirmacao=2)
    monkeypatch.setattr(page.controle_acesso, 'abrir', lambda: pytest.fail('GPIO should not be used'))
    events = []
    page.logger.registrar = lambda *args: events.append(args)
    page.verificar_acesso('pessoa exemplo')
    assert 'CONFIRMANDO' in page.status_acesso.text()
    page.verificar_acesso('pessoa exemplo')
    assert 'LIBERADO' in page.status_acesso.text()
    assert events[-1][:2] == ('pessoa exemplo', 'LIBERADO')
    assert events[-1][2].startswith('Rosto confirmado; modo sem relé')
    assert events[-1][3] == 'ENTRADA'
    page.verificar_acesso('Desconhecido')
    assert 'BLOQUEADO' in page.status_acesso.text()
    page.verificar_acesso('outra pessoa')
    assert 'SEM AUTORIZAÇÃO' in page.status_acesso.text()
    page.close()


def test_relay_enabled_waits_for_result(app, monkeypatch):
    import interface.paginas.pagina_camera as module
    page = PaginaCamera()
    # These tests isolate prior behavior; model rejection is covered by test_anti_spoof.
    page.antispoof_atual = dict(state='live', count=5, score=.99, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    page.variacao_atual = dict(count=5, different=True, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    page.config.update(pessoas_autorizadas=['pessoa exemplo'], rele_ativo=True, frames_confirmacao=2)
    calls = []
    class Thread:
        def __init__(self, target, args, **kwargs):
            calls.append((target, args))
        def start(self):
            pass
    monkeypatch.setattr(module.threading, 'Thread', Thread)
    page.logger.registrar = lambda *args: None
    page.verificar_acesso('pessoa exemplo'); page.verificar_acesso('pessoa exemplo')
    assert len(calls) == 1
    assert 'LIBERADO' not in page.status_acesso.text()
    page._mostrar_resultado_porta(False, 'pessoa exemplo')
    assert 'ERRO NO RELÉ' in page.status_acesso.text()
    page.close()


def test_old_config_cannot_restore_head_turn():
    c = configuracoes._validar({'vivacidade_ativa': True, 'vivacidade_frames': 9})
    assert not c['rele_ativo']
    assert not any(k.startswith('vivacidade_') for k in c)


def test_cancelled_login_blocks_all_admin_routes(app, monkeypatch):
    monkeypatch.setattr(PaginaCamera, 'iniciar_camera', lambda self: None)
    monkeypatch.setattr(AdminDialog, 'exec', lambda self: QDialog.Rejected)
    window = JanelaPrincipal()
    window.abrir_admin(); window.abrir_cadastro(); window.abrir_pessoas(); window.abrir_configuracoes()
    assert window.pagina_admin is None
    assert window.pagina_cadastro is None
    assert window.pagina_pessoas is None
    assert window.pagina_config is None
    window.close()


def test_expiry_blocks_mutations_and_returns_camera(app, monkeypatch):
    monkeypatch.setattr(PaginaCamera, 'iniciar_camera', lambda self: None)
    window = JanelaPrincipal()
    window.admin_autenticado = True
    window.ultima_atividade_admin = time.monotonic()
    window.abrir_cadastro()
    assert window.pagina_cadastro is not None
    window.ultima_atividade_admin -= 121
    page = window.pagina_cadastro
    monkeypatch.setattr(page.store, 'salvar_perfil', lambda *args: pytest.fail('Expired session wrote a profile'))
    page.finalizar_cadastro()
    window.bloquear_admin()
    assert window.paginas.currentWidget() is window.pagina_camera
    assert not window.admin_valido()
    window.close()


def test_direct_unauthenticated_mutation_is_denied(app, monkeypatch):
    page = PaginaConfiguracoes()
    import interface.paginas.pagina_configuracoes as config_module
    monkeypatch.setattr(config_module, 'salvar_configuracoes', lambda *args: pytest.fail('Unauthorized config write'))
    page.salvar(); page.restaurar_padrao()
    people = PaginaPessoas()
    monkeypatch.setattr(people.store, 'excluir', lambda *args: pytest.fail('Unauthorized delete'))
    people.confirmar_exclusao('pessoa exemplo')
    page.close(); people.close()


def test_password_dialog_setup_and_wrong_login(app, tmp_path):
    auth = AdminAuth(tmp_path/'auth.json')
    first = AdminDialog(auth)
    first.senha.setText('senha-exemplo'); first.confirmacao.setText('outra-senha')
    first.validar(); assert not auth.configurado()
    first.senha.setText('senha-exemplo'); first.confirmacao.setText('senha-exemplo')
    first.validar(); assert first.result() == QDialog.Accepted
    login = AdminDialog(auth)
    login.senha.setText('senha-errada'); login.validar()
    assert login.result() != QDialog.Accepted
    login.senha.setText('senha-exemplo'); login.validar()
    assert login.result() == QDialog.Accepted
    first.close(); login.close()
