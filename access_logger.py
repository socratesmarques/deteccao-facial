from __future__ import annotations

from collections import deque
import csv
from datetime import datetime
import os
from pathlib import Path
import tempfile
import threading

from app_paths import PRIVATE_DATA_DIR


class AccessLogger:
    """Histórico local. Migra CSV antigo preservando datas, decisões e detalhes."""
    LEGACY_HEADER = ['data_hora', 'pessoa', 'decisao', 'detalhe']
    HEADER = LEGACY_HEADER + ['movimento']
    _lock = threading.RLock()

    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path is not None else PRIVATE_DATA_DIR / 'acessos.csv'

    def _preparar(self):
        if not self.path.exists() or self.path.stat().st_size == 0:
            return
        with self.path.open(encoding='utf-8', newline='') as source:
            reader = csv.DictReader(source)
            if reader.fieldnames == self.HEADER:
                return
            if reader.fieldnames != self.LEGACY_HEADER:
                raise ValueError('Formato do histórico não reconhecido; arquivo preservado.')
            fd, temp = tempfile.mkstemp(prefix='acessos_', suffix='.csv', dir=self.path.parent)
            try:
                with os.fdopen(fd, 'w', encoding='utf-8', newline='') as target:
                    writer = csv.DictWriter(target, fieldnames=self.HEADER)
                    writer.writeheader()
                    for row in reader:
                        # Registros anteriores não informavam sentido. Não inferir entrada/saída.
                        writer.writerow(dict(row, movimento=''))
                    target.flush()
                    os.fsync(target.fileno())
                source.close()
                os.replace(temp, self.path)
            finally:
                if os.path.exists(temp):
                    os.unlink(temp)

    def registrar(self, pessoa: str, decisao: str, detalhe: str = '', movimento: str = ''):
        if movimento not in ('', 'ENTRADA', 'SAIDA'):
            raise ValueError('Movimento deve ser ENTRADA ou SAIDA.')
        row = dict(data_hora=datetime.now().astimezone().isoformat(timespec='seconds'),
                   pessoa=(pessoa or 'Desconhecido').strip(), decisao=decisao.strip().upper(),
                   detalhe=detalhe, movimento=movimento)
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self._preparar()
            new = not self.path.exists() or self.path.stat().st_size == 0
            with self.path.open('a', encoding='utf-8', newline='') as target:
                writer = csv.DictWriter(target, fieldnames=self.HEADER)
                if new:
                    writer.writeheader()
                writer.writerow(row)

    def listar(self, pessoa='', movimento='', decisao='', data='', limite=500):
        """Mais recentes primeiro; filtros aplicados antes do limite de memória."""
        with self._lock:
            if not self.path.exists():
                return []
            rows = deque(maxlen=limite)
            with self.path.open(encoding='utf-8', newline='') as source:
                reader = csv.DictReader(source)
                if reader.fieldnames not in (self.HEADER, self.LEGACY_HEADER, None):
                    raise ValueError('Formato do histórico não reconhecido.')
                for row in reader:
                    if not all(row.get(k) is not None for k in self.LEGACY_HEADER):
                        continue
                    row.setdefault('movimento', '')
                    if pessoa.casefold() not in row['pessoa'].casefold():
                        continue
                    if movimento and row['movimento'] != movimento:
                        continue
                    if decisao and row['decisao'] != decisao:
                        continue
                    if data and row['data_hora'][:10] != data:
                        continue
                    rows.append(row)
            return list(reversed(rows))
