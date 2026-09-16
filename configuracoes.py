import json
import os


ARQUIVO_CONFIG = "config.json"


CONFIG_PADRAO = {
    "camera": "/dev/video2",
    "limiar_reconhecimento": 0.45,
    "confianca_deteccao": 0.80,
    "mostrar_fps": False
}


def carregar_configuracoes():

    if not os.path.exists(ARQUIVO_CONFIG):
        salvar_configuracoes(CONFIG_PADRAO.copy())
        return CONFIG_PADRAO.copy()

    try:
        with open(
            ARQUIVO_CONFIG,
            "r",
            encoding="utf-8"
        ) as arquivo:

            configuracoes = json.load(
                arquivo
            )

        # Adiciona configurações novas caso
        # o config.json seja de uma versão antiga.
        resultado = CONFIG_PADRAO.copy()

        resultado.update(
            configuracoes
        )

        return resultado

    except Exception as erro:

        print(
            "Erro ao carregar configurações:",
            erro
        )

        return CONFIG_PADRAO.copy()


def salvar_configuracoes(configuracoes):

    try:

        with open(
            ARQUIVO_CONFIG,
            "w",
            encoding="utf-8"
        ) as arquivo:

            json.dump(
                configuracoes,
                arquivo,
                indent=4,
                ensure_ascii=False
            )

        return True

    except Exception as erro:

        print(
            "Erro ao salvar configurações:",
            erro
        )

        return False