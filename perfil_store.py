from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path

import numpy as np

from app_paths import PROFILES_FILE, ensure_private_data_dir


NOME_VALIDO = re.compile(r"^[\wÀ-ÿ .'-]{2,60}$", re.UNICODE)


def normalizar_nome(nome: str) -> str:
    nome = " ".join(nome.strip().lower().split())
    if not NOME_VALIDO.fullmatch(nome):
        raise ValueError("Use um nome entre 2 e 60 caracteres, sem símbolos especiais.")
    return nome


class PerfilStore:
    """Persistência atômica e centralizada dos perfis faciais."""

    def __init__(self, arquivo: str | Path = PROFILES_FILE):
        self.arquivo = Path(arquivo)

    def carregar(self) -> tuple[np.ndarray, np.ndarray]:
        if not self.arquivo.exists():
            return (
                np.empty((0, 128), dtype=np.float32),
                np.array([], dtype=str),
            )

        try:
            with np.load(self.arquivo, allow_pickle=False) as dados:
                perfis = np.asarray(dados["perfis"], dtype=np.float32)
                nomes = np.asarray(dados["nomes"], dtype=str)
        except (OSError, ValueError, KeyError) as erro:
            raise RuntimeError(f"Arquivo de perfis inválido: {erro}") from erro

        if perfis.ndim != 2 or len(perfis) != len(nomes):
            raise RuntimeError("O arquivo de perfis está inconsistente.")
        return perfis, nomes

    def listar(self) -> list[str]:
        _, nomes = self.carregar()
        return sorted(str(nome) for nome in nomes)

    def salvar_perfil(self, nome: str, perfil: np.ndarray) -> None:
        nome = normalizar_nome(nome)
        perfil = np.asarray(perfil, dtype=np.float32).flatten()
        norma = float(np.linalg.norm(perfil))
        if norma == 0:
            raise ValueError("O perfil facial gerado é inválido.")
        perfil /= norma

        perfis, nomes_array = self.carregar()
        nomes = [str(item) for item in nomes_array]
        if nome in nomes:
            perfis[nomes.index(nome)] = perfil
        else:
            perfis = perfil.reshape(1, -1) if len(perfis) == 0 else np.vstack((perfis, perfil))
            nomes.append(nome)
        self._salvar_atomico(perfis, np.asarray(nomes, dtype=str))

    def excluir(self, nome: str) -> bool:
        nome = normalizar_nome(nome)
        perfis, nomes = self.carregar()
        mascara = nomes != nome
        if bool(np.all(mascara)):
            return False
        self._salvar_atomico(perfis[mascara], nomes[mascara])
        return True

    def _salvar_atomico(self, perfis: np.ndarray, nomes: np.ndarray) -> None:
        ensure_private_data_dir()
        self.arquivo.parent.mkdir(parents=True, exist_ok=True)
        descritor, temporario = tempfile.mkstemp(
            prefix="perfis_", suffix=".npz", dir=self.arquivo.parent
        )
        os.close(descritor)
        try:
            np.savez(
                temporario,
                perfis=np.asarray(perfis, dtype=np.float32),
                nomes=np.asarray(nomes, dtype=str),
            )
            os.replace(temporario, self.arquivo)
        finally:
            if os.path.exists(temporario):
                os.unlink(temporario)
