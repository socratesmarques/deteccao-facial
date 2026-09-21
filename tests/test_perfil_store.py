import numpy as np
import pytest
from perfil_store import PerfilStore, normalizar_nome


def test_cria_atualiza_e_exclui_perfil(tmp_path):
    store = PerfilStore(tmp_path / "perfis.npz")
    store.salvar_perfil("Sócrates Costa", np.ones(128, dtype=np.float32))
    store.salvar_perfil("sócrates costa", np.arange(1, 129, dtype=np.float32))
    perfis, nomes = store.carregar()
    assert perfis.shape == (1, 128)
    assert nomes.tolist() == ["sócrates costa"]
    assert np.isclose(np.linalg.norm(perfis[0]), 1.0)
    assert store.excluir("Sócrates Costa") is True
    assert store.listar() == []


def test_rejeita_nome_invalido():
    with pytest.raises(ValueError):
        normalizar_nome("../arquivo")
