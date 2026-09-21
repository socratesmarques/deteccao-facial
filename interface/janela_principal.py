"""Interface V2: câmera em destaque e administração sob demanda."""
import time

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QApplication, QDialog, QFrame, QHBoxLayout, QLabel, QMainWindow, QPushButton,
    QScrollArea, QStackedWidget, QVBoxLayout, QWidget,
)

from interface.paginas.pagina_camera import PaginaCamera
from interface.tema import TEMA
from admin_auth import AdminAuth
from interface.admin_dialog import AdminDialog


class JanelaPrincipal(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FaceAI V2.4 — Controle de acesso")
        self.auth = AdminAuth()
        self.admin_autenticado = False
        self.ultima_atividade_admin = 0.0
        self.admin_timer = QTimer(self)
        self.admin_timer.setSingleShot(True)
        self.admin_timer.timeout.connect(self.bloquear_admin)
        QApplication.instance().installEventFilter(self)
        self.pagina_admin = None
        self.pagina_logs = None
        self.resize(1024, 768)
        self.setMinimumSize(640, 400)
        self.setStyleSheet(TEMA)
        self.pagina_cadastro = None
        self.pagina_pessoas = None
        self.pagina_config = None
        self._containers = {}

        central = QWidget()
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.setCentralWidget(central)

        cabecalho = QFrame(); cabecalho.setObjectName("cabecalho")
        topo = QHBoxLayout(cabecalho)
        topo.setContentsMargins(18, 8, 18, 8)
        marca = QLabel("FaceAI"); marca.setObjectName("marca")
        versao = QLabel("V2.4  /  ACESSO FACIAL"); versao.setObjectName("subtitulo")
        topo.addWidget(marca); topo.addWidget(versao); topo.addStretch()
        self.botao_voltar = QPushButton("← Câmera / Bloquear")
        self.botao_voltar.clicked.connect(self.abrir_camera)
        self.botao_voltar.hide()
        topo.addWidget(self.botao_voltar)
        self.botao_menu = QPushButton("Admin")
        self.botao_menu.clicked.connect(self.abrir_admin)
        topo.addWidget(self.botao_menu)
        layout.addWidget(cabecalho)
        self.paginas = QStackedWidget()
        layout.addWidget(self.paginas, 1)
        self.pagina_camera = PaginaCamera()
        self.paginas.addWidget(self.pagina_camera)
        self.atalho_tela = QShortcut(QKeySequence("F11"), self)
        self.atalho_tela.activated.connect(self.alternar_tela_cheia)
        self.atalho_escape = QShortcut(QKeySequence("Escape"), self)
        self.atalho_escape.activated.connect(self.sair_tela_cheia)
        self.abrir_camera()

    def admin_valido(self):
        return self.admin_autenticado and time.monotonic() - self.ultima_atividade_admin < 120

    def eventFilter(self, watched, event):
        if self.admin_valido() and event.type() in (
            QEvent.KeyPress, QEvent.MouseButtonPress, QEvent.TouchBegin, QEvent.Wheel
        ):
            if isinstance(watched, QWidget) and (watched is self or self.isAncestorOf(watched)):
                self.ultima_atividade_admin = time.monotonic()
                self.admin_timer.start(120_000)
        return super().eventFilter(watched, event)

    def _exigir_admin(self):
        if self.admin_valido():
            return True
        self.admin_autenticado = False
        dialog = AdminDialog(self.auth, self)
        resultado = dialog.exec()
        dialog.deleteLater()
        if resultado != QDialog.Accepted:
            return False
        self.admin_autenticado = True
        self.ultima_atividade_admin = time.monotonic()
        self.admin_timer.start(120_000)
        return True

    def bloquear_admin(self):
        self.admin_autenticado = False
        self.admin_timer.stop()
        modal = QApplication.activeModalWidget()
        if isinstance(modal, QDialog) and self.isAncestorOf(modal):
            modal.reject()
        self.abrir_camera()

    def abrir_admin(self):
        if not self._exigir_admin() or not self.pagina_camera.parar_camera():
            return
        self._parar_cadastro()
        def criar():
            pagina = QWidget()
            layout = QVBoxLayout(pagina)
            layout.setContentsMargins(24, 24, 24, 24)
            titulo = QLabel("Painel administrativo")
            titulo.setStyleSheet("font-size: 26px; font-weight: 700;")
            layout.addWidget(titulo)
            info = QLabel("Sessão protegida · bloqueio após 2 minutos sem interação")
            info.setWordWrap(True)
            layout.addWidget(info)
            for texto, acao in (
                ("Cadastrar pessoa", self.abrir_cadastro),
                ("Pessoas cadastradas", self.abrir_pessoas),
                ("Logs de entrada e saída", self.abrir_logs),
                ("Configurações e autorizações", self.abrir_configuracoes),
                ("Alterar senha", self.alterar_senha),
                ("Reiniciar câmera e bloquear", self.reiniciar_camera),
            ):
                botao = QPushButton(texto)
                botao.clicked.connect(acao)
                layout.addWidget(botao)
            layout.addStretch()
            return pagina
        self._pagina_administrativa("pagina_admin", criar)

    def abrir_logs(self):
        if not self._exigir_admin() or not self.pagina_camera.parar_camera():
            return
        self._parar_cadastro()
        from interface.paginas.pagina_logs import PaginaLogs
        pagina = self._pagina_administrativa("pagina_logs", lambda: PaginaLogs(self.admin_valido))
        pagina.atualizar()

    def alterar_senha(self):
        if self._exigir_admin():
            dialog = AdminDialog(self.auth, self, alterar=True)
            dialog.exec()
            dialog.deleteLater()

    def alternar_tela_cheia(self):
        self.showNormal() if self.isFullScreen() else self.showFullScreen()

    def sair_tela_cheia(self):
        if self.isFullScreen():
            self.showNormal()

    def _parar_cadastro(self):
        if self.pagina_cadastro is not None:
            if self.pagina_cadastro.cadastrando:
                self.pagina_cadastro.cancelar_cadastro()
            else:
                self.pagina_cadastro.parar_camera()

    def _pagina_administrativa(self, atributo, fabrica):
        pagina = getattr(self, atributo)
        if pagina is None:
            pagina = fabrica()
            setattr(self, atributo, pagina)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setWidget(pagina)
            self._containers[atributo] = scroll
            self.paginas.addWidget(scroll)
        self.paginas.setCurrentWidget(self._containers[atributo])
        self.botao_voltar.show()
        return pagina

    def abrir_camera(self):
        self.admin_autenticado = False
        self.admin_timer.stop()
        self._parar_cadastro()
        self.paginas.setCurrentWidget(self.pagina_camera)
        self.botao_voltar.hide()
        worker = self.pagina_camera.worker
        if worker is None or not worker.is_alive():
            self.pagina_camera.iniciar_camera()

    def reiniciar_camera(self):
        self._parar_cadastro()
        if self.pagina_camera.parar_camera():
            self.abrir_camera()

    def abrir_cadastro(self):
        if not self._exigir_admin() or not self.pagina_camera.parar_camera():
            return
        from interface.paginas.pagina_cadastro import PaginaCadastro
        self._pagina_administrativa("pagina_cadastro", lambda: PaginaCadastro(self.admin_valido))

    def abrir_pessoas(self):
        if not self._exigir_admin() or not self.pagina_camera.parar_camera():
            return
        self._parar_cadastro()
        from interface.paginas.pagina_pessoas import PaginaPessoas
        def criar():
            pagina = PaginaPessoas(self.admin_valido)
            pagina.recadastrar.connect(self.recadastrar_pessoa)
            return pagina
        self._pagina_administrativa("pagina_pessoas", criar).carregar_pessoas()

    def abrir_configuracoes(self):
        if not self._exigir_admin() or not self.pagina_camera.parar_camera():
            return
        self._parar_cadastro()
        from interface.paginas.pagina_configuracoes import PaginaConfiguracoes
        pagina = self._pagina_administrativa("pagina_config", lambda: PaginaConfiguracoes(self.admin_valido))
        pagina.detectar_cameras()
        pagina.carregar()

    def recadastrar_pessoa(self, nome):
        self.abrir_cadastro()
        if self.pagina_cadastro is not None and self.paginas.currentWidget() is self._containers.get("pagina_cadastro"):
            self.pagina_cadastro.preparar_recadastro(nome)

    def closeEvent(self, event):
        if not self.pagina_camera.parar_camera():
            event.ignore()
            return
        self.pagina_camera.controle_acesso.desconectar()
        self._parar_cadastro()
        self.admin_timer.stop()
        QApplication.instance().removeEventFilter(self)
        event.accept()
