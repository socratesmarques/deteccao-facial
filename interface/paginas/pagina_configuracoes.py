import glob

from PySide6.QtWidgets import (
    QCheckBox, QComboBox, QDoubleSpinBox, QFormLayout, QGroupBox, QLabel,
    QLineEdit, QMessageBox, QPushButton, QSpinBox, QVBoxLayout, QWidget,
)

from configuracoes import CONFIG_PADRAO, carregar_configuracoes, salvar_configuracoes


class PaginaConfiguracoes(QWidget):
    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)
        titulo = QLabel("Configurações")
        titulo.setStyleSheet("font-size: 28px; font-weight: bold;")
        layout.addWidget(titulo)

        grupo = QGroupBox("Câmera e desempenho")
        form = QFormLayout(grupo)
        self.camera = QComboBox()
        self.perfil = QComboBox()
        self.perfil.addItems(["auto", "notebook", "orange_pi"])
        self.largura = QSpinBox(); self.largura.setRange(320, 1920)
        self.altura = QSpinBox(); self.altura.setRange(240, 1080)
        self.fps = QSpinBox(); self.fps.setRange(5, 60)
        self.deteccao = QSpinBox(); self.deteccao.setRange(160, 1280)
        self.intervalo_rec = QDoubleSpinBox(); self.intervalo_rec.setRange(0, 2); self.intervalo_rec.setSingleStep(0.05)
        form.addRow("Largura da detecção:", self.deteccao)
        form.addRow("Intervalo do reconhecimento (s):", self.intervalo_rec)
        form.addRow("Perfil:", self.perfil)
        form.addRow("Dispositivo:", self.camera)
        form.addRow("Largura:", self.largura)
        form.addRow("Altura:", self.altura)
        form.addRow("FPS desejado:", self.fps)
        layout.addWidget(grupo)

        grupo_rec = QGroupBox("Reconhecimento e acesso")
        rec = QFormLayout(grupo_rec)
        self.limiar = QDoubleSpinBox(); self.limiar.setRange(0, 1); self.limiar.setSingleStep(0.01)
        self.confianca = QDoubleSpinBox(); self.confianca.setRange(0.1, 1); self.confianca.setSingleStep(0.05)
        self.frames = QSpinBox(); self.frames.setRange(2, 30)
        self.cooldown = QSpinBox(); self.cooldown.setRange(1, 300)
        self.porta = QLineEdit()
        self.autorizados = QLineEdit()
        self.autorizados.setPlaceholderText("socrates, alisson")
        self.mostrar_fps = QCheckBox("Mostrar FPS")
        rec.addRow("Limiar:", self.limiar)
        rec.addRow("Confiança da detecção:", self.confianca)
        rec.addRow("Frames de confirmação:", self.frames)
        rec.addRow("Intervalo entre aberturas:", self.cooldown)
        rec.addRow("Porta do ESP32:", self.porta)
        rec.addRow("Pessoas autorizadas:", self.autorizados)
        rec.addRow("", self.mostrar_fps)
        layout.addWidget(grupo_rec)
        salvar = QPushButton("Salvar configurações")
        salvar.clicked.connect(self.salvar)
        layout.addWidget(salvar)
        layout.addStretch()
        self.detectar_cameras()
        self.carregar()

    def detectar_cameras(self):
        atual = self.camera.currentText()
        self.camera.clear()
        dispositivos = sorted(glob.glob("/dev/video*"))
        self.camera.addItems(dispositivos or ["/dev/video0"])
        indice = self.camera.findText(atual)
        if indice >= 0:
            self.camera.setCurrentIndex(indice)

    def carregar(self):
        c = carregar_configuracoes()
        indice = self.camera.findText(str(c["camera"]))
        if indice < 0:
            self.camera.addItem(str(c["camera"])); indice = self.camera.count() - 1
        self.camera.setCurrentIndex(indice)
        self.perfil.setCurrentText(c["perfil_hardware"])
        self.deteccao.setValue(c["largura_deteccao"])
        self.intervalo_rec.setValue(c["intervalo_reconhecimento"])
        self.largura.setValue(c["largura_camera"]); self.altura.setValue(c["altura_camera"])
        self.fps.setValue(c["fps_camera"]); self.limiar.setValue(c["limiar_reconhecimento"])
        self.confianca.setValue(c["confianca_deteccao"]); self.frames.setValue(c["frames_confirmacao"])
        self.cooldown.setValue(c["cooldown_acesso"]); self.porta.setText(c["porta_esp32"])
        self.autorizados.setText(", ".join(c["pessoas_autorizadas"]))
        self.mostrar_fps.setChecked(c["mostrar_fps"])

    def salvar(self):
        config = carregar_configuracoes()
        config.update({
            "largura_deteccao": self.deteccao.value(), "intervalo_reconhecimento": self.intervalo_rec.value(),
            "perfil_hardware": self.perfil.currentText(), "camera": self.camera.currentText(),
            "largura_camera": self.largura.value(), "altura_camera": self.altura.value(),
            "fps_camera": self.fps.value(), "limiar_reconhecimento": self.limiar.value(),
            "confianca_deteccao": self.confianca.value(), "frames_confirmacao": self.frames.value(),
            "cooldown_acesso": self.cooldown.value(), "porta_esp32": self.porta.text().strip(),
            "pessoas_autorizadas": [n.strip() for n in self.autorizados.text().split(",") if n.strip()],
            "mostrar_fps": self.mostrar_fps.isChecked(),
        })
        if salvar_configuracoes(config):
            QMessageBox.information(self, "Configurações", "Configurações salvas com sucesso.")
        else:
            QMessageBox.critical(self, "Erro", "Não foi possível salvar as configurações.")

    def restaurar_padrao(self):
        salvar_configuracoes(CONFIG_PADRAO)
        self.carregar()
