from __future__ import annotations

import random
import time


class HeadTurnLiveness:
    """Desafio simples de vivacidade: neutro -> virar para um lado aleatorio."""

    def __init__(self, limiar: float = 0.18, frames: int = 2, timeout: float = 8.0):
        self.limiar = float(limiar)
        self.frames_necessarios = int(frames)
        self.timeout = float(timeout)
        self.reset()

    def reset(self) -> None:
        self.desafio = None
        self.inicio = 0.0
        self.neutro_visto = False
        self.frames_direcao = 0
        self.concluido = False

    def iniciar(self, agora: float | None = None) -> str:
        self.desafio = random.choice(("esquerda", "direita"))
        self.inicio = time.monotonic() if agora is None else float(agora)
        self.neutro_visto = False
        self.frames_direcao = 0
        self.concluido = False
        return self.desafio

    def atualizar(self, desvio_nariz: float | None, agora: float | None = None) -> str:
        if self.desafio is None:
            return "inativo"
        agora = time.monotonic() if agora is None else float(agora)
        if agora - self.inicio > self.timeout:
            self.reset()
            return "expirado"
        if desvio_nariz is None:
            self.frames_direcao = 0
            return "aguardando"

        valor = float(desvio_nariz)
        # Antes de aceitar a virada, exige que o rosto tenha aparecido aproximadamente de frente.
        if not self.neutro_visto:
            if abs(valor) <= self.limiar * 0.55:
                self.neutro_visto = True
            return "neutro"

        # YuNet: desvio positivo = nariz para a direita da imagem. Para a pessoa em frente
        # a camera, isso corresponde a virar para a propria esquerda.
        atingiu = valor >= self.limiar if self.desafio == "esquerda" else valor <= -self.limiar
        self.frames_direcao = self.frames_direcao + 1 if atingiu else 0
        if self.frames_direcao >= self.frames_necessarios:
            self.concluido = True
            return "concluido"
        return "virando"


def desvio_nariz_yunet(rosto) -> float | None:
    """Retorna deslocamento horizontal do nariz normalizado pela distancia entre os olhos."""
    if rosto is None or len(rosto) < 10:
        return None
    olho1_x, olho1_y = float(rosto[4]), float(rosto[5])
    olho2_x, olho2_y = float(rosto[6]), float(rosto[7])
    nariz_x = float(rosto[8])
    distancia_olhos = ((olho2_x - olho1_x) ** 2 + (olho2_y - olho1_y) ** 2) ** 0.5
    if distancia_olhos < 1.0:
        return None
    centro_olhos_x = (olho1_x + olho2_x) / 2.0
    return (nariz_x - centro_olhos_x) / distancia_olhos
