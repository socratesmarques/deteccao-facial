from __future__ import annotations

import cv2
import numpy as np

from app_paths import SFACE_MODEL, YUNET_MODEL


class FaceEngine:
    """Única implementação de detecção, embedding e reconhecimento."""

    def __init__(self, confianca: float = 0.8):
        if not YUNET_MODEL.exists() or not SFACE_MODEL.exists():
            raise FileNotFoundError("Modelos YuNet/SFace não encontrados na pasta modelos.")
        self.detector = cv2.FaceDetectorYN.create(
            str(YUNET_MODEL), "", (640, 480), float(confianca), 0.3, 5000
        )
        self.reconhecedor = cv2.FaceRecognizerSF.create(str(SFACE_MODEL), "")

    def configurar_confianca(self, confianca: float) -> None:
        self.detector.setScoreThreshold(float(confianca))

    def detectar(self, frame) -> np.ndarray:
        altura, largura = frame.shape[:2]
        self.detector.setInputSize((largura, altura))
        _, rostos = self.detector.detect(frame)
        return np.empty((0, 15), dtype=np.float32) if rostos is None else rostos

    def embedding(self, frame, rosto) -> np.ndarray:
        alinhado = self.reconhecedor.alignCrop(frame, rosto)
        vetor = self.reconhecedor.feature(alinhado).flatten().astype(np.float32)
        norma = float(np.linalg.norm(vetor))
        if norma == 0:
            raise ValueError("Não foi possível extrair características do rosto.")
        return vetor / norma

    @staticmethod
    def criar_perfil(embeddings: list[np.ndarray]) -> np.ndarray:
        if not embeddings:
            raise ValueError("Nenhum rosto válido foi capturado.")
        perfil = np.mean(np.asarray(embeddings, dtype=np.float32), axis=0)
        norma = float(np.linalg.norm(perfil))
        if norma == 0:
            raise ValueError("Não foi possível gerar o perfil facial.")
        return (perfil / norma).astype(np.float32)

    @staticmethod
    def reconhecer(
        embedding: np.ndarray,
        perfis: np.ndarray,
        nomes: np.ndarray,
        limiar: float,
    ) -> tuple[str, float]:
        if len(perfis) == 0:
            return "Desconhecido", 0.0

        # Perfis e embedding normalizados: produto escalar = similaridade cosseno.
        scores = np.asarray(perfis, dtype=np.float32) @ np.asarray(embedding, dtype=np.float32)
        indice = int(np.argmax(scores))
        score = float(scores[indice])
        return (str(nomes[indice]), score) if score >= limiar else ("Desconhecido", score)
