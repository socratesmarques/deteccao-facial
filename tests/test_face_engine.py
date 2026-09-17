import numpy as np
from face_engine import FaceEngine


def test_comparacao_vetorizada():
    perfis = np.eye(3, dtype=np.float32)
    nomes = np.array(["ana", "bia", "caio"])
    nome, score = FaceEngine.reconhecer(np.array([0, 1, 0], dtype=np.float32), perfis, nomes, 0.46)
    assert nome == "bia"
    assert score == 1.0


def test_resultado_desconhecido_abaixo_do_limiar():
    nome, _ = FaceEngine.reconhecer(
        np.array([0, 1], dtype=np.float32), np.array([[1, 0]], dtype=np.float32),
        np.array(["ana"]), 0.46,
    )
    assert nome == "Desconhecido"


def test_rescale_all_landmarks_without_scaling_confidence():
    class Detector:
        def setInputSize(self, size):
            self.size = size
        def detect(self, frame):
            self.frame_shape = frame.shape
            return None, np.array([[10, 20, 30, 40] + [15, 25]*5 + [0.9]], dtype=np.float32)
    engine = FaceEngine.__new__(FaceEngine)
    engine.detector = Detector()
    faces = engine.detectar(np.zeros((481, 640, 3), dtype=np.uint8), largura_maxima=320)
    assert engine.detector.size == (320, 240)
    np.testing.assert_allclose(faces[0, [0, 2, 4, 6, 8, 10, 12]], [20, 60, 30, 30, 30, 30, 30])
    np.testing.assert_allclose(faces[0, [1, 3, 5, 7, 9, 11, 13]], np.array([20, 40, 25, 25, 25, 25, 25]) * 481/240)
    assert abs(faces[0, 14] - 0.9) < 1e-6
