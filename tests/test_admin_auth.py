import json
import os
import time

import pytest
from admin_auth import AdminAuth


def test_password_is_hashed_and_verified(tmp_path):
    auth = AdminAuth(tmp_path / 'admin.json')
    auth.criar('senha-exemplo-123')
    raw = auth.path.read_text()
    assert 'senha-exemplo-123' not in raw
    assert auth.verificar('senha-exemplo-123')
    assert not auth.verificar('senha-incorreta')
    if os.name == 'posix':
        assert auth.path.stat().st_mode & 0o777 == 0o600
    with pytest.raises(RuntimeError):
        auth.criar('outra-senha-123')


def test_lockout_survives_reopening(tmp_path):
    path = tmp_path / 'admin.json'
    auth = AdminAuth(path)
    auth.criar('senha-exemplo-123')
    for _ in range(5):
        assert not auth.verificar('incorreta')
    with pytest.raises(ValueError, match='Aguarde'):
        AdminAuth(path).verificar('senha-exemplo-123')
    data = json.loads(path.read_text()); data['locked_until'] = time.time()-1
    path.write_text(json.dumps(data))
    assert auth.verificar('senha-exemplo-123')


def test_change_requires_current_password(tmp_path):
    auth = AdminAuth(tmp_path / 'admin.json')
    auth.criar('senha-original')
    with pytest.raises(ValueError):
        auth.alterar('incorreta', 'senha-alterada')
    assert auth.verificar('senha-original')
    auth.alterar('senha-original', 'senha-alterada')
    assert not auth.verificar('senha-original')
    assert auth.verificar('senha-alterada')


def test_corrupt_credentials_do_not_allow_setup(tmp_path):
    path = tmp_path / 'admin.json'
    path.write_text('{}')
    auth = AdminAuth(path)
    assert auth.configurado()
    with pytest.raises(RuntimeError):
        auth.verificar('senha-qualquer')
    with pytest.raises(RuntimeError):
        auth.criar('senha-qualquer')
