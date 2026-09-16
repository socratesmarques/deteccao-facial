import os
import shutil
import numpy as np

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QFrame,
    QMessageBox,
    QLineEdit
)

from PySide6.QtCore import Signal

class PaginaPessoas(QWidget):

    # Avisa a JanelaPrincipal que alguém
    # quer recadastrar uma pessoa
    recadastrar = Signal(str)

    def __init__(self):
        super().__init__()

        self.ARQUIVO_PERFIS = "perfis.npz"
        self.PASTA_DADOS = "dados"
    
        # =========================
        # INTERFACE
        # =========================

        self.layout = QVBoxLayout(self)

        titulo = QLabel(
            "Pessoas Cadastradas"
        )

        titulo.setStyleSheet(
            "font-size: 28px; "
            "font-weight: bold;"
        )

        self.total = QLabel(
            "0 pessoas cadastradas"
        )
        self.pesquisa = QLineEdit()

        self.pesquisa.setPlaceholderText(
            "Pesquisar pessoa..."
        )

        self.pesquisa.textChanged.connect(
            self.carregar_pessoas
        )

        self.botao_atualizar = QPushButton(
            "Atualizar lista"
        )

        self.botao_atualizar.clicked.connect(
            self.carregar_pessoas
        )

        self.layout.addWidget(titulo)
        self.layout.addWidget(self.total)
        self.layout.addWidget(
            self.botao_atualizar
        )

        # =========================
        # ÁREA ROLÁVEL
        # =========================

        self.scroll = QScrollArea()

        self.scroll.setWidgetResizable(
            True
        )

        self.container = QWidget()

        self.lista_layout = QVBoxLayout(
            self.container
        )

        self.lista_layout.addStretch()

        self.scroll.setWidget(
            self.container
        )

        self.layout.addWidget(
            self.scroll
        )

        # Carrega inicialmente
        self.carregar_pessoas()


    # =============================
    # LIMPAR LISTA
    # =============================

    def limpar_lista(self):

        while self.lista_layout.count() > 1:

            item = self.lista_layout.takeAt(0)

            widget = item.widget()

            if widget is not None:
                widget.deleteLater()


    # =============================
    # CARREGAR PESSOAS
    # =============================

    def carregar_pessoas(self):

        self.limpar_lista()

        if not os.path.exists(
            self.ARQUIVO_PERFIS
        ):

            self.total.setText(
                "Nenhuma pessoa cadastrada"
            )

            return

        try:

            dados = np.load(
                self.ARQUIVO_PERFIS
            )

            nomes = dados["nomes"]

        except Exception as erro:

            self.total.setText(
                "Erro ao carregar os perfis."
            )

            print(
                "Erro ao carregar perfis:",
                erro
            )

            return

        quantidade = len(nomes)

        # =========================
        # TOTAL
        # =========================

        if quantidade == 0:

            self.total.setText(
                "Nenhuma pessoa cadastrada"
            )

        elif quantidade == 1:

            self.total.setText(
                "1 pessoa cadastrada"
            )

        else:

            self.total.setText(
                f"{quantidade} pessoas cadastradas"
            )

        # =========================
        # CARDS
        # =========================

        for nome in nomes:

            card = self.criar_card(
                str(nome)
            )

            self.lista_layout.insertWidget(
                self.lista_layout.count() - 1,
                card
            )


    # =============================
    # CRIAR CARD
    # =============================

    def criar_card(self, nome):

        card = QFrame()

        card.setStyleSheet(
            """
            QFrame {
                border: 1px solid #555;
                border-radius: 10px;
                padding: 10px;
            }
            """
        )

        layout = QHBoxLayout(card)

        # =========================
        # INFORMAÇÕES
        # =========================

        informacoes = QVBoxLayout()

        label_nome = QLabel(
            nome.title()
        )

        label_nome.setStyleSheet(
            """
            font-size: 18px;
            font-weight: bold;
            """
        )

        status = QLabel(
            "● Perfil facial ativo"
        )

        # =========================
        # QUANTIDADE DE IMAGENS
        # =========================

        pasta_pessoa = os.path.join(
            self.PASTA_DADOS,
            nome
        )

        quantidade = 0

        if os.path.exists(
            pasta_pessoa
        ):

            quantidade = len([
                arquivo
                for arquivo in os.listdir(
                    pasta_pessoa
                )
                if arquivo.lower().endswith(
                    (
                        ".jpg",
                        ".jpeg",
                        ".png"
                    )
                )
            ])

        if quantidade == 1:

            texto_imagens = (
                "1 imagem cadastrada"
            )

        else:

            texto_imagens = (
                f"{quantidade} imagens cadastradas"
            )

        label_imagens = QLabel(
            texto_imagens
        )

        informacoes.addWidget(
            label_nome
        )

        informacoes.addWidget(
            status
        )

        informacoes.addWidget(
            label_imagens
        )

        layout.addLayout(
            informacoes
        )

        layout.addStretch()

        # =========================
        # RECADASTRAR
        # =========================

        botao_recadastrar = QPushButton(
            "Recadastrar"
        )

        botao_recadastrar.clicked.connect(
            lambda: self.recadastrar.emit(
                nome
            )
        )

        layout.addWidget(
            botao_recadastrar
        )

        # =========================
        # EXCLUIR
        # =========================

        botao_excluir = QPushButton(
            "Excluir"
        )

        botao_excluir.clicked.connect(
            lambda: self.confirmar_exclusao(
                nome
            )
        )

        layout.addWidget(
            botao_excluir
        )

        return card

    # =============================
    # CONFIRMAR EXCLUSÃO
    # =============================

    def confirmar_exclusao(
        self,
        nome
    ):

        resposta = QMessageBox.question(
            self,
            "Excluir pessoa",
            (
                f"Tem certeza que deseja excluir "
                f"{nome.title()}?\n\n"
                "O perfil facial e todas as fotos "
                "dessa pessoa serão apagados."
            ),
            QMessageBox.Yes |
            QMessageBox.No,
            QMessageBox.No
        )

        if resposta == QMessageBox.Yes:

            self.excluir_pessoa(
                nome
            )


    # =============================
    # EXCLUIR PESSOA
    # =============================

    def excluir_pessoa(
        self,
        nome
    ):

        if not os.path.exists(
            self.ARQUIVO_PERFIS
        ):

            QMessageBox.warning(
                self,
                "Erro",
                "Arquivo de perfis não encontrado."
            )

            return

        try:

            # =========================
            # CARREGA PERFIS
            # =========================

            dados = np.load(
                self.ARQUIVO_PERFIS
            )

            perfis = dados[
                "perfis"
            ]

            nomes = dados[
                "nomes"
            ]

            # =========================
            # REMOVE A PESSOA
            # =========================

            mascara = nomes != nome

            novos_perfis = perfis[
                mascara
            ]

            novos_nomes = nomes[
                mascara
            ]

            # =========================
            # SALVA
            # =========================

            np.savez(
                self.ARQUIVO_PERFIS,

                perfis=np.array(
                    novos_perfis,
                    dtype=np.float32
                ),

                nomes=np.array(
                    novos_nomes
                )
            )

            # =========================
            # REMOVE AS FOTOS
            # =========================

            pasta_pessoa = os.path.join(
                self.PASTA_DADOS,
                nome
            )

            if os.path.exists(
                pasta_pessoa
            ):

                shutil.rmtree(
                    pasta_pessoa
                )

            # =========================
            # ATUALIZA LISTA
            # =========================

            self.carregar_pessoas()

            QMessageBox.information(
                self,
                "Pessoa excluída",
                (
                    f"{nome.title()} foi "
                    "excluído com sucesso."
                )
            )

        except Exception as erro:

            print(
                "Erro ao excluir pessoa:",
                erro
            )

            QMessageBox.critical(
                self,
                "Erro",
                (
                    "Não foi possível excluir "
                    "a pessoa."
                )
            )