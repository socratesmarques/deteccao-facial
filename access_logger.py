from __future__ import annotations

import csv
import threading
from datetime import datetime
from pathlib import Path

from app_paths import PRIVATE_DATA_DIR, ensure_private_data_dir


class AccessLogger:
    """Registra decisões de acesso em CSV local, fora do Git."""

    HEADER = ["data_hora", "pessoa", "decisao", "detalhe"]

    def __init__(self, path: Path | None = None):
        ensure_private_data_dir()
        self.path = path or (PRIVATE_DATA_DIR / "acessos.csv")
        self._lock = threading.Lock()

    def registrar(self, pessoa: str, decisao: str, detalhe: str = "") -> None:
        pessoa = (pessoa or "Desconhecido").strip()
        decisao = decisao.strip().upper()
        momento = datetime.now().astimezone().isoformat(timespec="seconds")
        with self._lock:
            novo = not self.path.exists()
            with self.path.open("a", encoding="utf-8", newline="") as arquivo:
                writer = csv.writer(arquivo)
                if novo:
                    writer.writerow(self.HEADER)
                writer.writerow([momento, pessoa, decisao, detalhe])
