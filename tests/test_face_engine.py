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
