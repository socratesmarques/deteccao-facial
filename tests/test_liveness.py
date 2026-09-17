from liveness import HeadTurnLiveness, desvio_nariz_yunet


def test_desvio_nariz_normalizado():
    rosto = [0, 0, 100, 100, 30, 40, 70, 40, 60, 60, 0, 0, 0, 0, 0]
    assert abs(desvio_nariz_yunet(rosto) - 0.25) < 1e-6


def test_exige_neutro_antes_da_virada():
    live = HeadTurnLiveness(limiar=0.18, frames=2, timeout=8)
    live.desafio = "esquerda"
    live.inicio = 10.0
    assert live.atualizar(0.30, 10.1) == "neutro"
    assert not live.neutro_visto
    assert live.atualizar(0.02, 10.2) == "neutro"
    assert live.neutro_visto
    assert live.atualizar(0.25, 10.3) == "virando"
    assert live.atualizar(0.25, 10.4) == "concluido"


def test_timeout_reseta_desafio():
    live = HeadTurnLiveness(timeout=3)
    live.desafio = "direita"
    live.inicio = 5.0
    assert live.atualizar(0.0, 8.1) == "expirado"
    assert live.desafio is None
