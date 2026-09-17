from __future__ import annotations

import copy
import json
import os
import tempfile

from app_paths import CONFIG_FILE


CONFIG_PADRAO = {
    "perfil_hardware": "auto", "camera": "/dev/video0",
    "largura_camera": 640, "altura_camera": 480, "fps_camera": 20,
    "largura_deteccao": 320, "intervalo_reconhecimento": 0.35,
    "processar_a_cada_frames": 1, "limiar_reconhecimento": 0.46,
    "confianca_deteccao": 0.80, "mostrar_fps": True,
    "quantidade_cadastro": 20, "intervalo_cadastro": 0.55,
    "frames_confirmacao": 5, "cooldown_acesso": 10,
    "porta_esp32": "/dev/ttyACM0", "baudrate_esp32": 115200,
    "pessoas_autorizadas": ["socrates"],
}


def _validar(config: dict) -> dict:
    resultado = copy.deepcopy(CONFIG_PADRAO)
    resultado.update(config if isinstance(config, dict) else {})
    resultado["largura_deteccao"] = min(1280, max(160, int(resultado["largura_deteccao"])))
    resultado["intervalo_reconhecimento"] = min(2.0, max(0.0, float(resultado["intervalo_reconhecimento"])))
    resultado["largura_camera"] = max(320, int(resultado["largura_camera"]))
    resultado["altura_camera"] = max(240, int(resultado["altura_camera"]))
    resultado["fps_camera"] = min(60, max(5, int(resultado["fps_camera"])))
    resultado["processar_a_cada_frames"] = min(5, max(1, int(resultado["processar_a_cada_frames"])))
    resultado["limiar_reconhecimento"] = min(1.0, max(0.0, float(resultado["limiar_reconhecimento"])))
    resultado["confianca_deteccao"] = min(1.0, max(0.1, float(resultado["confianca_deteccao"])))
    resultado["quantidade_cadastro"] = min(50, max(5, int(resultado["quantidade_cadastro"])))
    resultado["intervalo_cadastro"] = min(3.0, max(0.2, float(resultado["intervalo_cadastro"])))
    resultado["frames_confirmacao"] = min(30, max(2, int(resultado["frames_confirmacao"])))
    resultado["cooldown_acesso"] = min(300, max(1, int(resultado["cooldown_acesso"])))
    resultado["baudrate_esp32"] = int(resultado["baudrate_esp32"])
    resultado["pessoas_autorizadas"] = sorted({
        str(nome).strip().lower() for nome in resultado.get("pessoas_autorizadas", [])
        if str(nome).strip()
    })
    return resultado


def carregar_configuracoes() -> dict:
    if not CONFIG_FILE.exists():
        salvar_configuracoes(CONFIG_PADRAO)
        return copy.deepcopy(CONFIG_PADRAO)
    try:
        with CONFIG_FILE.open("r", encoding="utf-8") as arquivo:
            return _validar(json.load(arquivo))
    except (OSError, ValueError, TypeError) as erro:
        print("Erro ao carregar configurações; usando padrão:", erro)
        return copy.deepcopy(CONFIG_PADRAO)


def salvar_configuracoes(configuracoes: dict) -> bool:
    config = _validar(configuracoes)
    temporario = None
    try:
        descritor, temporario = tempfile.mkstemp(prefix="config_", suffix=".json", dir=CONFIG_FILE.parent)
        with os.fdopen(descritor, "w", encoding="utf-8") as arquivo:
            json.dump(config, arquivo, indent=4, ensure_ascii=False)
            arquivo.write("\n")
        os.replace(temporario, CONFIG_FILE)
        return True
    except OSError as erro:
        print("Erro ao salvar configurações:", erro)
        return False
    finally:
        if temporario and os.path.exists(temporario):
            os.unlink(temporario)
