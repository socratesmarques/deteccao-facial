"""Senha administrativa local; nenhum segredo padrão ou em texto puro."""
from __future__ import annotations

import hashlib
import hmac
import json
import os
from pathlib import Path
import secrets
import tempfile
import time

from app_paths import PRIVATE_DATA_DIR


class AdminAuth:
    ITERATIONS = 600_000

    def __init__(self, path: Path | None = None):
        self.path = path if path is not None else PRIVATE_DATA_DIR / 'admin.json'

    def configurado(self):
        return self.path.exists()

    def _ler(self):
        try:
            data = json.loads(self.path.read_text(encoding='utf-8'))
            if (data['version'] != 1 or data['iterations'] != self.ITERATIONS
                    or len(bytes.fromhex(data['salt'])) != 32
                    or len(bytes.fromhex(data['hash'])) != 32
                    or not isinstance(data['failures'], int)
                    or not isinstance(data['locked_until'], (int, float))):
                raise ValueError('Formato inválido')
            return data
        except (ValueError, KeyError, TypeError, OSError) as error:
            raise RuntimeError('Não foi possível ler a senha administrativa. Verifique o arquivo local admin.json.') from error

    def _salvar(self, data):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        fd, temp = tempfile.mkstemp(prefix='admin_', suffix='.json', dir=self.path.parent)
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as out:
                json.dump(data, out)
                out.flush()
                os.fsync(out.fileno())
            os.replace(temp, self.path)
        finally:
            if os.path.exists(temp):
                os.unlink(temp)

    @staticmethod
    def validar_senha(password):
        if len(password) < 8 or not password.strip():
            raise ValueError('Use uma senha com pelo menos 8 caracteres.')
        if len(password) > 256:
            raise ValueError('Use no máximo 256 caracteres.')

    def _novo_registro(self, password):
        self.validar_senha(password)
        salt = secrets.token_bytes(32)
        digest = hashlib.pbkdf2_hmac('sha256', password.encode(), salt, self.ITERATIONS)
        return dict(version=1, salt=salt.hex(), hash=digest.hex(), iterations=self.ITERATIONS,
                    failures=0, locked_until=0)

    def criar(self, password):
        if self.configurado():
            raise RuntimeError('A senha administrativa já foi configurada.')
        self._salvar(self._novo_registro(password))

    def verificar(self, password):
        data = self._ler()
        remaining = data['locked_until'] - time.time()
        if remaining > 0:
            raise ValueError(f'Muitas tentativas. Aguarde {int(remaining) + 1} segundos.')
        digest = hashlib.pbkdf2_hmac('sha256', password[:257].encode(), bytes.fromhex(data['salt']), self.ITERATIONS)
        valid = len(password) <= 256 and hmac.compare_digest(digest.hex(), data['hash'])
        if valid:
            data.update(failures=0, locked_until=0)
        else:
            data['failures'] += 1
            if data['failures'] >= 5:
                data.update(failures=0, locked_until=time.time() + 30)
        self._salvar(data)
        return valid

    def alterar(self, current, new):
        self.validar_senha(new)
        if not self.verificar(current):
            raise ValueError('Senha atual incorreta.')
        self._salvar(self._novo_registro(new))
