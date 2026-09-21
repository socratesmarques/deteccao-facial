import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import csv
import time
from datetime import datetime
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication, QDialog
import app_paths
import access_logger
import configuracoes
import perfil_store
from access_logger import AccessLogger
from recognition_worker import RecognitionWorker
from single_face import SingleFaceProcessor
from interface.paginas.pagina_camera import PaginaCamera
from interface.paginas.pagina_cadastro import PaginaCadastro
from interface.paginas.pagina_pessoas import PaginaPessoas
from interface.paginas.pagina_logs import PaginaLogs
from interface.janela_principal import JanelaPrincipal
from interface.admin_dialog import AdminDialog


@pytest.fixture
def app(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(app_paths, 'PRIVATE_DATA_DIR', tmp_path)
    monkeypatch.setattr(access_logger, 'PRIVATE_DATA_DIR', tmp_path)
    monkeypatch.setattr(configuracoes, 'CONFIG_FILE', tmp_path/'config.json')
    def store_init(self, arquivo=None):
        self.arquivo = tmp_path/'perfis.npz'
    monkeypatch.setattr(perfil_store.PerfilStore, '__init__', store_init)
    return app


def cadastrar(autorizar=True):
    page = PaginaCadastro(lambda: True)
    page.nome_atual = 'pessoa exemplo'
    page.embeddings = [np.ones(128, dtype=np.float32)]
    page.autorizar.setChecked(autorizar)
    page.finalizar_cadastro()
    assert 'concluído' in page.status.text()
    page.close()


class ApprovedAntiSpoof:
    def analyze(self, frame, face):
        return dict(state='live', score=.99, reason='Test double')


class Engine:
    def __init__(self):
        self.faces = [np.array([10,10,80,80]+[0]*10+[0.99])]
        self.name = 'pessoa exemplo'
    def detectar(self, frame, largura_maxima):
        return self.faces
    def embedding(self, *args):
        return np.ones(128)
    def reconhecer(self, *args):
        return self.name, 0.99


def send(page, worker, processor, now):
    frame = np.full((100,100,3), 80, dtype=np.uint8)
    offset = int(round(now * 2.5)) % 2 * 20
    frame[30:55, 25+offset:45+offset] = 200
    face, name, score, fresh, gen = processor.process(frame, now)
    proof = processor.variation.snapshot()
    proof['sampled_at'] = time.monotonic()
    anti = processor.anti_spoof_window.snapshot()
    anti['sampled_at'] = time.monotonic()
    result = dict(frame=frame, name=name, fresh=fresh, visible=face is not None, variation=proof, antispoof=anti,
                  generation=gen, observations=processor.confirmations, encounter=processor.target.encounter,
                  captured=time.monotonic(), error=None)
    worker.publish(result)
    return result


def test_registration_to_entry_exit_and_admin_logs_with_dropped_frames(app, monkeypatch):
    cadastrar()
    page = PaginaCamera()
    # These tests isolate prior behavior; model rejection is covered by test_anti_spoof.
    page.antispoof_atual = dict(state='live', count=5, score=.99, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    page.variacao_atual = dict(count=5, different=True, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    monkeypatch.setattr(page.controle_acesso, 'abrir', lambda: pytest.fail('Unexpected GPIO call'))
    worker = RecognitionWorker(page.config, page.perfis, page.nomes)
    monkeypatch.setattr(worker, 'stop', lambda: True)
    page.worker = worker
    processor = SingleFaceProcessor(Engine(), page.perfis, page.nomes, page.config, ApprovedAntiSpoof())
    # Five actual inferences, each fresh frame overwritten by a cached preview frame.
    for now in (0, .4, .8, 1.2, 1.6):
        send(page, worker, processor, now)
        result = send(page, worker, processor, now+.01)
        assert not result['fresh']
    page.atualizar_camera()
    assert 'LIBERADO' in page.status_acesso.text()
    assert 'ENTRADA' in page.status_acesso.text()
    # Keep recognition going past cooldown: one event for this presence.
    send(page, worker, processor, 20)
    page.atualizar_camera()
    assert len(page.logger.listar(decisao='LIBERADO')) == 1
    page.selecionar_movimento('SAIDA')
    send(page, worker, processor, 20.01)
    page.atualizar_camera()
    assert 'LIBERADO' not in page.status_acesso.text()  # no reused confirmations
    for now in (20.4,20.8,21.2,21.6,22):
        send(page, worker, processor, now)
    page.atualizar_camera()
    assert 'SAÍDA' in page.status_acesso.text()
    rows = page.logger.listar(decisao='LIBERADO')
    assert [r['movimento'] for r in rows] == ['SAIDA', 'ENTRADA']
    assert all(datetime.fromisoformat(r['data_hora']).tzinfo is not None for r in rows)
    logs = PaginaLogs(lambda: True)
    assert logs.tabela.rowCount() == 2
    logs.movimento.setCurrentIndex(2)
    assert logs.tabela.rowCount() == 1
    assert logs.tabela.item(0,2).text() == 'Saída'
    logs.close(); page.close()


def test_existing_blocked_profile_requires_explicit_authorization(app):
    cadastrar(False)
    page = PaginaCamera()
    # These tests isolate prior behavior; model rejection is covered by test_anti_spoof.
    page.antispoof_atual = dict(state='live', count=5, score=.99, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    page.variacao_atual = dict(count=5, different=True, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    for _ in range(5):
        page.verificar_acesso('pessoa exemplo')
    assert 'SEM AUTORIZAÇÃO' in page.status_acesso.text()
    assert not page.logger.listar(decisao='LIBERADO')
    people = PaginaPessoas(lambda: True)
    people.alterar_autorizacao('pessoa exemplo', True)
    page.carregar_configuracoes()
    for _ in range(5):
        page.verificar_acesso('pessoa exemplo')
    assert 'LIBERADO' in page.status_acesso.text()
    assert len(page.logger.listar(decisao='LIBERADO')) == 1
    people.close(); page.close()


def test_loss_or_unknown_resets_accumulated_inferences(app):
    cadastrar()
    page = PaginaCamera()
    # These tests isolate prior behavior; model rejection is covered by test_anti_spoof.
    page.antispoof_atual = dict(state='live', count=5, score=.99, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    page.variacao_atual = dict(count=5, different=True, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    engine = Engine()
    p = SingleFaceProcessor(engine, page.perfis, page.nomes, page.config)
    for now in (0,.4,.8):
        p.process(None,now)
    assert p.confirmations == 3
    old = p.evidence_epoch
    engine.name = 'Desconhecido'
    p.process(None,1.2)
    engine.name = 'pessoa exemplo'
    p.process(None,1.6)
    assert p.evidence_epoch != old
    assert p.confirmations == 1
    engine.faces = []
    p.process(None,2)
    assert p.confirmations == 0
    page.close()


def test_stale_snapshot_cannot_contribute_to_next_confirmation(app, monkeypatch):
    cadastrar()
    page = PaginaCamera()
    # These tests isolate prior behavior; model rejection is covered by test_anti_spoof.
    page.antispoof_atual = dict(state='live', count=5, score=.99, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    page.variacao_atual = dict(count=5, different=True, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    worker = RecognitionWorker(page.config, page.perfis, page.nomes)
    monkeypatch.setattr(worker, 'stop', lambda: True)
    page.worker = worker
    base = dict(frame=np.zeros((20,20,3),dtype=np.uint8), generation=1, fresh=False,
                name='pessoa exemplo', visible=True, error=None)
    worker.publish(dict(base, observations=5, captured=time.monotonic()-2))
    page.atualizar_camera()
    worker.publish(dict(base, observations=6, captured=time.monotonic()))
    page.atualizar_camera()
    assert page.frames_confirmados == 1
    assert 'LIBERADO' not in page.status_acesso.text()
    page.close()


def test_legacy_log_migration_preserves_history(tmp_path):
    path = tmp_path/'acessos.csv'
    with path.open('w', newline='') as f:
        w = csv.writer(f)
        w.writerow(AccessLogger.LEGACY_HEADER)
        w.writerow(['2026-09-20T12:00:00-03:00','pessoa antiga','LIBERADO','evento anterior'])
    log = AccessLogger(path)
    assert log.listar()[0]['movimento'] == ''
    log.registrar('pessoa exemplo','LIBERADO','Sem relé','SAIDA')
    rows = log.listar()
    assert len(rows) == 2
    assert rows[1]['data_hora'] == '2026-09-20T12:00:00-03:00'
    assert rows[1]['detalhe'] == 'evento anterior'
    assert rows[1]['movimento'] == ''
    assert log.listar(pessoa='ANTIGA', data='2026-09-20')[0] == rows[1]
    assert len(log.listar(movimento='SAIDA')) == 1


def test_logs_require_admin_and_handle_disk_error(app, monkeypatch):
    logs = PaginaLogs()
    monkeypatch.setattr(logs.logger,'listar', lambda **kwargs: pytest.fail('Unauthenticated read'))
    logs.atualizar()
    assert logs.tabela.rowCount() == 0
    monkeypatch.setattr(PaginaCamera, 'iniciar_camera', lambda self: None)
    monkeypatch.setattr(AdminDialog, 'exec', lambda self: QDialog.Rejected)
    window = JanelaPrincipal(); window.abrir_logs()
    assert window.pagina_logs is None
    logs.pode_administrar = lambda: True
    def failing(**kwargs):
        raise OSError('disco indisponível')
    monkeypatch.setattr(logs.logger,'listar',failing)
    logs.atualizar()
    assert 'disco indisponível' in logs.total.text()
    window.close(); logs.close()


def test_grant_stays_visible_if_log_write_fails(app, monkeypatch):
    cadastrar()
    page = PaginaCamera()
    # These tests isolate prior behavior; model rejection is covered by test_anti_spoof.
    page.antispoof_atual = dict(state='live', count=5, score=.99, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    page.variacao_atual = dict(count=5, different=True, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    def failing(*args):
        raise OSError('sem espaço')
    monkeypatch.setattr(page.logger,'registrar',failing)
    for _ in range(5):
        page.verificar_acesso('pessoa exemplo')
    assert 'LIBERADO' in page.status_acesso.text()
    assert 'ERRO ao salvar log' in page.status_acesso.text()
    page.close()
