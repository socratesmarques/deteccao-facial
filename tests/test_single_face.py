import numpy as np

from configuracoes import CONFIG_PADRAO
from single_face import SingleFace, SingleFaceProcessor


def face(x=0, size=100):
    return np.array([x, 0, size, size] + [0]*10 + [0.99], dtype=np.float32)


def test_keeps_target_when_larger_person_enters():
    tracker = SingleFace()
    tracker.select([face()], 0)
    assert tracker.select([face(200, 200), face(5)], 0.1)[0] == 5


def test_loss_hides_immediately_and_delays_new_target():
    tracker = SingleFace()
    tracker.select([face()], 0)
    assert tracker.select([face(300)], 0.1) is None
    assert tracker.select([face(300)], 0.9) is None
    assert tracker.select([face(300)], 1)[0] == 300


def test_brief_loss_invalidates_confirmation():
    tracker = SingleFace()
    tracker.select([face()], 0)
    initial = tracker.generation
    assert tracker.select([], 0.1) is None
    assert tracker.select([face(3)], 0.2) is not None
    assert tracker.generation > initial


def test_overlap_never_selects_other_person_after_timeout():
    tracker = SingleFace()
    tracker.select([face()], 0)
    for now in (0.1, 1, 3):
        assert tracker.select([face(2), face(-2)], now) is None
        assert tracker.box is not None
    assert tracker.select([face()], 4) is not None


class Engine:
    def __init__(self):
        self.calls = 0
        self.faces = [face(), face(300)]
        self.name = 'ana'

    def detectar(self, frame, largura_maxima):
        return self.faces

    def embedding(self, frame, rosto):
        self.calls += 1
        return np.ones(2)

    def reconhecer(self, *args):
        return self.name, 0.9


def processor():
    engine = Engine()
    return engine, SingleFaceProcessor(engine, np.ones((1, 2)), ['ana'], CONFIG_PADRAO)


def test_one_embedding_for_crowd_and_no_cached_confirmation():
    engine, p = processor()
    assert p.process(None, 0)[3]
    assert not p.process(None, 0.1)[3]
    assert p.process(None, 0.4)[3]
    assert engine.calls == 2


def test_no_embedding_with_no_profiles():
    engine, p = processor()
    p.profiles = []
    assert p.process(None, 0)[1] == 'Desconhecido'
    assert engine.calls == 0


def test_unknown_invalidates_evidence_even_if_result_dropped():
    engine, p = processor()
    epoch = p.process(None, 0)[4]
    engine.name = 'Desconhecido'
    p.process(None, 0.4)
    engine.name = 'ana'
    assert p.process(None, 0.8)[4] != epoch


def test_configured_stride_does_not_skip_presence_checks():
    engine, p = processor()
    p.config = dict(CONFIG_PADRAO, processar_a_cada_frames=5)
    p.process(None, 0)
    assert not p.process(None, 1)[3]
    engine.faces = []
    assert p.process(None, 2)[0] is None
    assert engine.calls == 1
