import glob

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QComboBox,
    QDoubleSpinBox,
    QCheckBox,
    QMessageBox,
    QGroupBox,
    QFormLayout
)

from configuracoes import (
    carregar_configuracoes,
    salvar_configuracoes
)


class PaginaConfiguracoes(QWidget):

    def __init__(self):
        super().__init__()

        self.criar_interface()
        self.carregar()

    # =============================
    # CRIAR INTERFACE
    # =============================

    def criar_interface(self):

        layout = QVBoxLayout(self)

        titulo = QLabel(
            "Configurações"
        )

        titulo.setStyleSheet(
            "font-size: 28px; "
            "font-weight: bold;"
        )

        descricao = QLabel(
            "Configure a câmera e o "
            "reconhecimento facial."
        )

        layout.addWidget(titulo)
        layout.addWidget(descricao)
        layout.addSpacing(20)

        # =========================
        # CÂMERA
        # =========================

        grupo_camera = QGroupBox(
            "Câmera"
        )

        camera_layout = QFormLayout(
            grupo_camera
        )

        self.camera = QComboBox()

        # Detecta automaticamente
        # as câmeras disponíveis.
        self.detectar_cameras()

        camera_layout.addRow(
            "Dispositivo:",
            self.camera
        )

        layout.addWidget(
            grupo_camera
        )

        # =========================
        # RECONHECIMENTO
        # =========================

        grupo_reconhecimento = QGroupBox(
            "Reconhecimento facial"
        )

        reconhecimento_layout = QFormLayout(
            grupo_reconhecimento
        )

        # =========================
        # LIMIAR
        # =========================

        self.limiar = QDoubleSpinBox()

        self.limiar.setRange(
            0.0,
            1.0
        )

        self.limiar.setSingleStep(
            0.01
        )

        self.limiar.setDecimals(
            2
        )

        reconhecimento_layout.addRow(
            "Limiar de reconhecimento:",
            self.limiar
        )

        # =========================
        # CONFIANÇA
        # =========================

        self.confianca = QDoubleSpinBox()

        self.confianca.setRange(
            0.0,
            1.0
        )

        self.confianca.setSingleStep(
            0.05
        )

        self.confianca.setDecimals(
            2
        )

        reconhecimento_layout.addRow(
            "Confiança da detecção:",
            self.confianca
        )

        # =========================
        # FPS
        # =========================

        self.mostrar_fps = QCheckBox(
            "Mostrar FPS na câmera"
        )

        reconhecimento_layout.addRow(
            "",
            self.mostrar_fps
        )

        layout.addWidget(
            grupo_reconhecimento
        )

        # =========================
        # EXPLICAÇÃO
        # =========================

        explicacao = QLabel(
            "Quanto maior o limiar, mais rigoroso "
            "será o reconhecimento. Valores muito "
            "altos podem fazer pessoas cadastradas "
            "aparecerem como desconhecidas."
        )

        explicacao.setWordWrap(
            True
        )

        layout.addWidget(
            explicacao
        )

        # =========================
        # BOTÕES
        # =========================

        botoes = QHBoxLayout()

        botao_padrao = QPushButton(
            "Restaurar padrão"
        )

        botao_salvar = QPushButton(
            "Salvar configurações"
        )

        botao_padrao.clicked.connect(
            self.restaurar_padrao
        )

        botao_salvar.clicked.connect(
            self.salvar
        )

        botoes.addStretch()

        botoes.addWidget(
            botao_padrao
        )

        botoes.addWidget(
            botao_salvar
        )

        layout.addStretch()
        layout.addLayout(botoes)

    # =============================
    # DETECTAR CÂMERAS
    # =============================

    def detectar_cameras(self):

        # Guarda a câmera que estava
        # selecionada anteriormente.
        camera_atual = (
            self.camera.currentText()
        )

        self.camera.clear()

        # Procura dispositivos de vídeo
        # existentes no Linux.
        dispositivos = sorted(
            glob.glob(
                "/dev/video*"
            )
        )

        # Adiciona os dispositivos
        # encontrados.
        for dispositivo in dispositivos:

            self.camera.addItem(
                dispositivo
            )

        # Nenhuma câmera encontrada.
        if not dispositivos:

            self.camera.addItem(
                "Nenhuma câmera encontrada"
            )

        # Tenta manter a câmera
        # anteriormente selecionada.
        if camera_atual:

            indice = self.camera.findText(
                camera_atual
            )

            if indice >= 0:

                self.camera.setCurrentIndex(
                    indice
                )

    # =============================
    # CARREGAR CONFIGURAÇÕES
    # =============================

    def carregar(self):

        config = carregar_configuracoes()

        camera_salva = config.get(
            "camera",
            "/dev/video2"
        )

        indice = self.camera.findText(
            camera_salva
        )

        # Caso a câmera salva não esteja
        # atualmente disponível.
        if indice == -1:

            self.camera.addItem(
                camera_salva
            )

            indice = self.camera.findText(
                camera_salva
            )

        self.camera.setCurrentIndex(
            indice
        )

        self.limiar.setValue(
            config.get(
                "limiar_reconhecimento",
                0.45
            )
        )

        self.confianca.setValue(
            config.get(
                "confianca_deteccao",
                0.80
            )
        )

        self.mostrar_fps.setChecked(
            config.get(
                "mostrar_fps",
                False
            )
        )

    # =============================
    # SALVAR
    # =============================

    def salvar(self):

        camera_selecionada = (
            self.camera.currentText()
        )

        if (
            camera_selecionada
            == "Nenhuma câmera encontrada"
        ):

            QMessageBox.warning(
                self,
                "Câmera",
                "Nenhuma câmera disponível."
            )

            return

        config = {
            "camera":
                camera_selecionada,

            "limiar_reconhecimento":
                self.limiar.value(),

            "confianca_deteccao":
                self.confianca.value(),

            "mostrar_fps":
                self.mostrar_fps.isChecked()
        }

        sucesso = salvar_configuracoes(
            config
        )

        if sucesso:

            QMessageBox.information(
                self,
                "Configurações",
                "Configurações salvas "
                "com sucesso."
            )

        else:

            QMessageBox.critical(
                self,
                "Erro",
                "Não foi possível salvar "
                "as configurações."
            )

    # =============================
    # RESTAURAR PADRÃO
    # =============================

    def restaurar_padrao(self):

        indice = self.camera.findText(
            "/dev/video2"
        )

        if indice >= 0:

            self.camera.setCurrentIndex(
                indice
            )

        self.limiar.setValue(
            0.45
        )

        self.confianca.setValue(
            0.80
        )

        self.mostrar_fps.setChecked(
            False
        )