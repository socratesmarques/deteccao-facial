import json
import configuracoes


def test_carrega_configuracao_parcial(tmp_path, monkeypatch):
    arquivo = tmp_path / "config.json"
    arquivo.write_text(json.dumps({"fps_camera": 999}), encoding="utf-8")
    monkeypatch.setattr(configuracoes, "CONFIG_FILE", arquivo)
    config = configuracoes.carregar_configuracoes()
    assert config["fps_camera"] == 60
    assert config["limiar_reconhecimento"] == 0.46


def test_normaliza_autorizados():
    config = configuracoes._validar({"pessoas_autorizadas": [" Sócrates ", "sócrates", ""]})
    assert config["pessoas_autorizadas"] == ["sócrates"]
