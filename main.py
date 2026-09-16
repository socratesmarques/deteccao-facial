import sys

from PySide6.QtWidgets import QApplication
from interface.janela_principal import JanelaPrincipal


app = QApplication(sys.argv)

janela = JanelaPrincipal()
janela.show()

sys.exit(app.exec())