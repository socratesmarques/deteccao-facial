from PySide6.QtWidgets import (
    QMainWindow,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QPushButton,
    QLabel,
    QStackedWidget
)

from PySide6.QtCore import Qt

from interface.paginas.pagina_camera import PaginaCamera
from interface.paginas.pagina_cadastro import PaginaCadastro
from interface.paginas.pagina_pessoas import PaginaPessoas
from interface.paginas.pagina_configuracoes import PaginaConfiguracoes


class JanelaPrincipal(QMainWindow):

    def __init__(self):
        super().__init__()

        self.setWindowTitle("FaceAI")
        self.resize(1100, 700)

        self.criar_interface()


    # =============================
    # CRIAR INTERFACE
    # =============================

    def criar_interface(self):

        central = QWidget()
        self.setCentralWidget(central)

        layout_principal = QHBoxLayout(
            central
        )


        # =========================
        # MENU
        # =========================

        menu = QVBoxLayout()

        titulo = QLabel("FaceAI")

        titulo.setAlignment(
            Qt.AlignCenter
        )

        titulo.setStyleSheet(
            "font-size: 26px; "
            "font-weight: bold;"
        )


        self.botao_camera = QPushButton(
            "Câmera"
        )

        self.botao_cadastrar = QPushButton(
            "Cadastrar pessoa"
        )

        self.botao_pessoas = QPushButton(
            "Pessoas cadastradas"
        )

        self.botao_config = QPushButton(
            "Configurações"
        )


        menu.addWidget(titulo)

        menu.addSpacing(30)

        menu.addWidget(
            self.botao_camera
        )

        menu.addWidget(
            self.botao_cadastrar
        )

        menu.addWidget(
            self.botao_pessoas
        )

        menu.addWidget(
            self.botao_config
        )

        menu.addStretch()


        # =========================
        # PÁGINAS
        # =========================

        self.paginas = QStackedWidget()


        self.pagina_camera = (
            PaginaCamera()
        )

        self.pagina_cadastro = (
            PaginaCadastro()
        )

        self.pagina_pessoas = (
            PaginaPessoas()
        )

        self.pagina_config = (
            PaginaConfiguracoes()
        )


        self.paginas.addWidget(
            self.pagina_camera
        )

        self.paginas.addWidget(
            self.pagina_cadastro
        )

        self.paginas.addWidget(
            self.pagina_pessoas
        )

        self.paginas.addWidget(
            self.pagina_config
        )


        # =========================
        # BOTÕES DO MENU
        # =========================

        self.botao_camera.clicked.connect(
            self.abrir_camera
        )

        self.botao_cadastrar.clicked.connect(
            self.abrir_cadastro
        )

        self.botao_pessoas.clicked.connect(
            self.abrir_pessoas
        )

        self.botao_config.clicked.connect(
            self.abrir_configuracoes
        )


        # =========================
        # SINAL DE RECADASTRO
        # =========================

        self.pagina_pessoas.recadastrar.connect(
            self.recadastrar_pessoa
        )


        # =========================
        # LAYOUT
        # =========================

        layout_principal.addLayout(
            menu,
            1
        )

        layout_principal.addWidget(
            self.paginas,
            4
        )


        # =========================
        # PÁGINA INICIAL
        # =========================

        self.abrir_camera()


    # =============================
    # ABRIR CÂMERA
    # =============================

    def abrir_camera(self):

        # Se cadastro estiver usando
        # a câmera, libera primeiro.
        if self.pagina_cadastro.cadastrando:

            self.pagina_cadastro.cancelar_cadastro()

        else:

            self.pagina_cadastro.parar_camera()


        # Recarrega perfis para pegar
        # cadastros novos.
        self.pagina_camera.carregar_perfis()


        self.paginas.setCurrentWidget(
            self.pagina_camera
        )


        self.pagina_camera.iniciar_camera()


    # =============================
    # ABRIR CADASTRO
    # =============================

    def abrir_cadastro(self):

        # Reconhecimento precisa liberar
        # a webcam antes.
        self.pagina_camera.parar_camera()


        self.paginas.setCurrentWidget(
            self.pagina_cadastro
        )


    # =============================
    # ABRIR PESSOAS
    # =============================

    def abrir_pessoas(self):

        self.pagina_camera.parar_camera()


        if self.pagina_cadastro.cadastrando:

            self.pagina_cadastro.cancelar_cadastro()

        else:

            self.pagina_cadastro.parar_camera()


        # Atualiza a lista sempre
        # que abrir a página.
        self.pagina_pessoas.carregar_pessoas()


        self.paginas.setCurrentWidget(
            self.pagina_pessoas
        )


    # =============================
    # ABRIR CONFIGURAÇÕES
    # =============================

    def abrir_configuracoes(self):

        self.pagina_camera.parar_camera()


        if self.pagina_cadastro.cadastrando:

            self.pagina_cadastro.cancelar_cadastro()

        else:

            self.pagina_cadastro.parar_camera()
        self.pagina_config.detectar_cameras()
        self.pagina_config.carregar()

        self.paginas.setCurrentWidget(
            self.pagina_config
        )


    # =============================
    # RECADASTRAR PESSOA
    # =============================

    def recadastrar_pessoa(
        self,
        nome
    ):

        # Garante que reconhecimento
        # liberou a webcam.
        self.pagina_camera.parar_camera()


        self.pagina_cadastro.preparar_recadastro(nome)


        # Abre página de cadastro.
        self.paginas.setCurrentWidget(
            self.pagina_cadastro
        )


        self.pagina_cadastro.status.setText(
            f"Pronto para recadastrar "
            f"{nome.title()}."
        )


    # =============================
    # FECHAR PROGRAMA
    # =============================

    def closeEvent(
        self,
        event
    ):

        self.pagina_camera.parar_camera()

        self.pagina_camera.controle_acesso.desconectar()

        self.pagina_cadastro.parar_camera()

        event.accept()
