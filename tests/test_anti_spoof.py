import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
import json
import time

import cv2
import numpy as np
import pytest
from PySide6.QtWidgets import QApplication
import app_paths
import access_logger
import configuracoes
from anti_spoof import AntiSpoofEngine, AntiSpoofWindow, MODEL_FILES, crop_patch, probabilities
from single_face import SingleFaceProcessor
from interface.paginas.pagina_camera import PaginaCamera


def test_crop_matches_expected_context_and_keeps_bgr_range():
    frame = np.zeros((480,640,3),np.uint8)
    frame[:,:,0] = 10; frame[:,:,1] = 70; frame[:,:,2] = 230
    box = [270,190,100,100]
    crop = crop_patch(frame,box,2.7)
    assert crop.shape == (80,80,3)
    np.testing.assert_array_equal(crop[40,40], [10,70,230])
    # Coordinate gradient checks inclusive cropping and default interpolation.
    frame[:,:,0] = np.arange(640,dtype=np.uint16)[None,:] % 256
    expected = cv2.resize(frame[105:376,185:456],(80,80))
    np.testing.assert_array_equal(crop_patch(frame,box,2.7),expected)
    edge = crop_patch(frame,[0,0,100,100],2.7)
    np.testing.assert_array_equal(edge,cv2.resize(frame[0:271,0:271],(80,80)))


def test_small_or_incomplete_faces_do_not_reach_model():
    engine = AntiSpoofEngine.__new__(AntiSpoofEngine)
    engine.nets = [(None,2.7),(None,4)]
    engine.threshold = .8
    frame = np.zeros((480,640,3),np.uint8)
    assert engine.analyze(frame,[10,10,20,20])['state'] == 'uncertain'
    assert engine.analyze(frame,[-20,10,100,100])['state'] == 'uncertain'


def fake_engine(logits):
    class Net:
        def __init__(self, values): self.values=values
        def setInput(self, blob):
            assert blob.shape == (1,3,80,80)
            assert blob.dtype == np.float32
        def forward(self): return np.array([self.values])
    engine=AntiSpoofEngine.__new__(AntiSpoofEngine)
    engine.threshold=.8
    engine.nets=[(Net(values),scale) for values,scale in zip(logits,[2.7,4])]
    return engine


@pytest.mark.parametrize('logits,state', [([[0,8,0],[0,8,0]],'live'),
    ([[8,0,0],[0,8,0]],'spoof'), ([[0,8,0],[0,0,8]],'spoof'),
    ([[0,8,0],[0,0,0]],'uncertain')])
def test_both_models_must_approve(logits,state):
    result=fake_engine(logits).analyze(np.full((480,640,3),100,np.uint8),[200,100,100,120])
    assert result['state']==state


def test_invalid_model_output_fails_closed():
    with pytest.raises(RuntimeError): probabilities([[np.nan,0,1]])
    with pytest.raises(RuntimeError): probabilities([[1,2]])


def test_window_needs_five_consecutive_approvals_after_rejection():
    window=AntiSpoofWindow()
    for i in range(4): window.add(dict(state='live',score=.95),i+1,i*.35)
    assert window.snapshot()['state']=='pending'
    window.add(dict(state='spoof',score=.01,reason='test'),5,1.4)
    assert window.snapshot()['state']=='spoof'
    for i in range(6,10): window.add(dict(state='live',score=.95),i,i*.35)
    assert window.snapshot()['state']=='pending'
    window.add(dict(state='live',score=.95),10,3.5)
    assert window.snapshot()['state']=='live'
    assert window.snapshot()['first_observation']==6
    window.add(dict(state='live',score=.95),11,7)
    assert window.snapshot()['count']==1


def test_real_bundled_models_execute_on_cpu_and_checksums(tmp_path):
    cv2.setNumThreads(2)
    engine=AntiSpoofEngine()
    result=engine.analyze(np.full((480,640,3),100,np.uint8),[220,140,100,120])
    assert result['state'] in ('live','spoof','uncertain')
    assert len(result['scores'])==2
    assert all(np.isfinite(v) and 0<=v<=1 for v in result['scores'])
    with pytest.raises(RuntimeError): AntiSpoofEngine(model_dir=tmp_path)
    (tmp_path/'manifest.json').write_text(json.dumps({'models':[{'file':MODEL_FILES[0][0], 'sha256':'invalid'}]}))
    (tmp_path/MODEL_FILES[0][0]).write_bytes(b'corrupt model')
    with pytest.raises(RuntimeError,match='corrompido'): AntiSpoofEngine(model_dir=tmp_path)


@pytest.fixture
def page(tmp_path,monkeypatch):
    app=QApplication.instance() or QApplication([])
    monkeypatch.setattr(app_paths,'PRIVATE_DATA_DIR',tmp_path)
    monkeypatch.setattr(access_logger,'PRIVATE_DATA_DIR',tmp_path)
    monkeypatch.setattr(configuracoes,'CONFIG_FILE',tmp_path/'config.json')
    page=PaginaCamera()
    page.config.update(pessoas_autorizadas=['pessoa exemplo'],frames_confirmacao=5)
    page.variacao_atual=dict(count=5,different=True,first_observation=1,sampled_at=time.monotonic())
    yield page
    page.close()


@pytest.mark.parametrize('relay',[False,True])
@pytest.mark.parametrize('state',['spoof','uncertain','error','pending'])
def test_rejection_blocks_access_even_when_five_frames_differ(page,monkeypatch,relay,state):
    import interface.paginas.pagina_camera as module
    page.config['rele_ativo']=relay
    page.antispoof_atual=dict(state=state,count=0,score=.1,reason='test rejection',first_observation=1,sampled_at=time.monotonic())
    monkeypatch.setattr(module.threading,'Thread',lambda *a,**kw:pytest.fail('Rejected sample reached relay'))
    for _ in range(5): page.verificar_acesso('pessoa exemplo')
    assert 'LIBERADO' not in page.status_acesso.text()
    assert not page.logger.listar(decisao='LIBERADO')
    if state in ('spoof','uncertain'):
        assert page.logger.listar(decisao='BLOQUEADO')
    if state=='error': assert page.logger.listar(decisao='ERRO')


def test_valid_evidence_expires_and_direction_needs_new_evidence(page):
    page.antispoof_atual=dict(state='live',count=5,score=.95,first_observation=1,sampled_at=time.monotonic()-4)
    for _ in range(5): page.verificar_acesso('pessoa exemplo')
    assert not page.logger.listar(decisao='LIBERADO')
    page.antispoof_atual['sampled_at']=time.monotonic()
    page.verificar_acesso('pessoa exemplo')
    assert len(page.logger.listar(decisao='LIBERADO'))==1
    old=page.antispoof_atual.copy()
    page.observacoes_vistas=5
    page.selecionar_movimento('SAIDA')
    page.antispoof_atual=old
    assert not page._conferir_antispoof('pessoa exemplo')


def test_processor_inference_exception_clears_prior_approvals():
    class Face:
        def detectar(self,*a,**kw): return [np.array([20,20,80,80]+[0]*10+[.99])]
        def embedding(self,*a):return np.ones(128)
        def reconhecer(self,*a):return 'pessoa exemplo',.99
    class Anti:
        fail=False
        def analyze(self,*a):
            if self.fail:raise RuntimeError('inference failed')
            return dict(state='live',score=.99)
    anti=Anti()
    config=dict(configuracoes.CONFIG_PADRAO,pessoas_autorizadas=['pessoa exemplo'])
    p=SingleFaceProcessor(Face(),np.ones((1,128)),['pessoa exemplo'],config,anti)
    for i in range(5):p.process(np.zeros((240,320,3),np.uint8),i*.4)
    assert p.anti_spoof_window.snapshot()['state']=='live'
    anti.fail=True
    p.process(np.zeros((240,320,3),np.uint8),2)
    assert p.anti_spoof_window.snapshot()['state']=='error'
    assert p.anti_spoof_window.snapshot()['count']==0
