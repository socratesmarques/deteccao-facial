"""Inicialização do FaceAI V2.4 no computador ou no display da caixa."""
import argparse
import sys
import cv2

from PySide6.QtWidgets import QApplication

from configuracoes import carregar_configuracoes
from interface.janela_principal import JanelaPrincipal


def main():
    parser = argparse.ArgumentParser(description="FaceAI V2.4 — controle de acesso facial")
    modo = parser.add_mutually_exclusive_group()
    modo.add_argument("--kiosk", action="store_true", help="Abre em tela cheia para o display da caixa")
    modo.add_argument("--windowed", action="store_true", help="Abre em janela para uso no computador")
    args = parser.parse_args()
    cv2.setNumThreads(2)
    app = QApplication([sys.argv[0]])
    app.setApplicationName("FaceAI V2.4")
    janela = JanelaPrincipal()
    tela_cheia = args.kiosk or (
        not args.windowed and carregar_configuracoes()["perfil_hardware"] == "orange_pi"
    )
    janela.showFullScreen() if tela_cheia else janela.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
