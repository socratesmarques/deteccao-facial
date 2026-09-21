import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
import time
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication
import app_paths
import access_logger
import configuracoes
from frame_variation import FrameVariation
from single_face import SingleFaceProcessor
from interface.paginas.pagina_camera import PaginaCamera


FACE = np.array([10,10,80,80]+[0]*10+[.99])


def frame(offset=0):
    result = np.full((100,100,3),80,dtype=np.uint8)
    result[30:55,25+offset:45+offset] = 200
    return result


@pytest.fixture
def page(tmp_path, monkeypatch):
    app = QApplication.instance() or QApplication([])
    monkeypatch.setattr(app_paths,'PRIVATE_DATA_DIR',tmp_path)
    monkeypatch.setattr(access_logger,'PRIVATE_DATA_DIR',tmp_path)
    monkeypatch.setattr(configuracoes,'CONFIG_FILE',tmp_path/'config.json')
    page = PaginaCamera()
    # These tests isolate prior behavior; model rejection is covered by test_anti_spoof.
    page.antispoof_atual = dict(state='live', count=5, score=.99, first_observation=1, last_observation=5, sampled_at=time.monotonic())
    page.config.update(pessoas_autorizadas=['pessoa exemplo'], frames_confirmacao=5)
    yield page
    page.close()


def submit(page, images):
    variation = FrameVariation()
    for i, image in enumerate(images):
        variation.observe(image, FACE, i+1, i*.35)
        page.variacao_atual = variation.snapshot()
        page.variacao_atual['sampled_at'] = time.monotonic()
        page.verificar_acesso('pessoa exemplo')
    return variation


@pytest.mark.parametrize('relay',[False, True])
def test_identical_frames_block_both_modes(page, monkeypatch, relay):
    import interface.paginas.pagina_camera as module
    page.config['rele_ativo'] = relay
    monkeypatch.setattr(module.threading, 'Thread', lambda *a,**kw: pytest.fail('Identical images reached GPIO thread'))
    submit(page, [frame()]*5)
    assert 'BLOQUEADO' in page.status_acesso.text()
    assert 'SEM VARIAÇÃO' in page.status_acesso.text()
    assert not page.logger.listar(decisao='LIBERADO')
    assert 'Cinco amostras' in page.logger.listar(decisao='BLOQUEADO')[0]['detalhe']


def test_only_releases_at_five_samples_with_variation(page):
    submit(page, [frame(),frame(20),frame(),frame(20)])
    assert 'LIBERADO' not in page.status_acesso.text()
    assert not page.logger.listar(decisao='LIBERADO')
    submit(page, [frame(),frame(),frame(20),frame(),frame()])
    assert 'LIBERADO' in page.status_acesso.text()
    assert len(page.logger.listar(decisao='LIBERADO')) == 1


def test_missing_or_expired_proof_is_denied(page):
    for _ in range(5):
        page.verificar_acesso('pessoa exemplo')
    assert 'LIBERADO' not in page.status_acesso.text()
    page.variacao_atual = dict(count=5,different=True,first_observation=1,last_observation=5,sampled_at=time.monotonic()-4)
    page.verificar_acesso('pessoa exemplo')
    assert not page.logger.listar(decisao='LIBERADO')


def test_direction_change_cannot_reuse_old_variation(page):
    submit(page, [frame(),frame(20),frame(),frame(),frame()])
    assert 'LIBERADO' in page.status_acesso.text()
    proof = page.variacao_atual.copy()
    page.observacoes_vistas = 5
    page.selecionar_movimento('SAIDA')
    page.variacao_atual = proof
    page.verificar_acesso('pessoa exemplo',5)
    assert 'LIBERADO' not in page.status_acesso.text()
    assert len(page.logger.listar(decisao='LIBERADO')) == 1


def test_face_loss_and_identity_change_reset_window():
    class Engine:
        face = FACE
        name = 'pessoa exemplo'
        def detectar(self, *args, **kwargs):
            return [self.face] if self.face is not None else []
        def embedding(self, *args):
            return np.ones(128)
        def reconhecer(self, *args):
            return self.name,.99
    engine = Engine()
    processor = SingleFaceProcessor(engine,np.ones((1,128)),np.array(['pessoa exemplo']),configuracoes.CONFIG_PADRAO)
    for i in range(5):
        processor.process(frame((i%2)*20),i*.4)
    assert processor.variation.snapshot()['count'] == 5
    engine.name = 'outra pessoa'
    processor.process(frame(),2)
    assert processor.variation.snapshot()['count'] == 1
    engine.face = None
    processor.process(frame(),2.4)
    assert processor.variation.snapshot()['count'] == 0
