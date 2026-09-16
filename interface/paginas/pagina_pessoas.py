from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QLineEdit, QMessageBox, QPushButton,
    QScrollArea, QVBoxLayout, QWidget,
)

from perfil_store import PerfilStore


class PaginaPessoas(QWidget):
    recadastrar = Signal(str)

    def __init__(self):
        super().__init__()
        self.store = PerfilStore()
        layout = QVBoxLayout(self)
        titulo = QLabel("Pessoas Cadastradas")
        titulo.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.total = QLabel()
        self.pesquisa = QLineEdit()
        self.pesquisa.setPlaceholderText("Pesquisar pessoa...")
        self.pesquisa.textChanged.connect(self.carregar_pessoas)
        atualizar = QPushButton("Atualizar lista")
        atualizar.clicked.connect(self.carregar_pessoas)
        layout.addWidget(titulo)
        layout.addWidget(self.total)
        layout.addWidget(self.pesquisa)
        layout.addWidget(atualizar)
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.container = QWidget()
        self.lista_layout = QVBoxLayout(self.container)
        self.lista_layout.addStretch()
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        self.carregar_pessoas()

    def limpar_lista(self):
        while self.lista_layout.count() > 1:
            item = self.lista_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

    def carregar_pessoas(self, *_):
        self.limpar_lista()
        try:
            nomes = self.store.listar()
        except RuntimeError as erro:
            self.total.setText(str(erro))
            return
        filtro = self.pesquisa.text().strip().lower()
        exibidos = [nome for nome in nomes if filtro in nome.lower()]
        self.total.setText(f"{len(nomes)} pessoa(s) cadastrada(s)")
        for nome in exibidos:
            self.lista_layout.insertWidget(self.lista_layout.count() - 1, self.criar_card(nome))

    def criar_card(self, nome):
        card = QFrame()
        card.setStyleSheet("QFrame { border: 1px solid #555; border-radius: 10px; padding: 10px; }")
        layout = QHBoxLayout(card)
        label = QLabel(f"{nome.title()}\n● Perfil facial ativo")
        label.setStyleSheet("font-size: 17px; font-weight: bold;")
        layout.addWidget(label)
        layout.addStretch()
        recadastrar = QPushButton("Recadastrar")
        recadastrar.clicked.connect(lambda: self.recadastrar.emit(nome))
        excluir = QPushButton("Excluir")
        excluir.clicked.connect(lambda: self.confirmar_exclusao(nome))
        layout.addWidget(recadastrar)
        layout.addWidget(excluir)
        return card

    def confirmar_exclusao(self, nome):
        resposta = QMessageBox.question(
            self, "Excluir pessoa", f"Excluir definitivamente o perfil facial de {nome.title()}?",
            QMessageBox.Yes | QMessageBox.No, QMessageBox.No,
        )
        if resposta != QMessageBox.Yes:
            return
        try:
            if self.store.excluir(nome):
                self.carregar_pessoas()
                QMessageBox.information(self, "Pessoa excluída", "Perfil removido com sucesso.")
        except (RuntimeError, OSError, ValueError) as erro:
            QMessageBox.critical(self, "Erro", str(erro))
