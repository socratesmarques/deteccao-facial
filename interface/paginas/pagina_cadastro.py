from __future__ import annotations

import time

import cv2
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QCheckBox, QHBoxLayout, QLabel, QLineEdit, QProgressBar, QPushButton, QVBoxLayout, QWidget,
)

from interface.camera_view import CameraView
from autorizacoes import definir_autorizacao
from camera_utils import abrir_camera
from configuracoes import carregar_configuracoes
from face_engine import FaceEngine
from perfil_store import PerfilStore, normalizar_nome


class PaginaCadastro(QWidget):
    def __init__(self, pode_administrar=lambda: False):
        super().__init__()
        self.pode_administrar = pode_administrar
        self.camera = None
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.atualizar_camera)
        self.engine = None
        self.store = PerfilStore()
        self.embeddings = []
        self.nome_atual = ""
        self.contador = 0
        self.ultima_captura = 0.0
        self.cadastrando = False
        self.modo_recadastro = False
        self.config = carregar_configuracoes()

        layout = QVBoxLayout(self)
        titulo = QLabel("Cadastrar Pessoa")
        titulo.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.nome = QLineEdit()
        self.nome.setPlaceholderText("Digite o nome da pessoa")
        self.autorizar = QCheckBox("Autorizar acesso ao concluir o cadastro")
        self.autorizar.setChecked(True)
        self.botao_iniciar = QPushButton("Iniciar cadastro")
        self.botao_cancelar = QPushButton("Cancelar")
        self.botao_cancelar.setEnabled(False)
        botoes = QHBoxLayout()
        botoes.addWidget(self.botao_iniciar)
        botoes.addWidget(self.botao_cancelar)
        self.camera_label = CameraView()
        self.camera_label.setMinimumHeight(200)
        self.camera_label.setText("Informe o nome e inicie o cadastro.")
        self.progresso = QProgressBar()
        self.status = QLabel("Aguardando cadastro...")
        self.status.setAlignment(Qt.AlignCenter)
        layout.addWidget(titulo)
        layout.addWidget(self.nome)
        layout.addWidget(self.autorizar)
        layout.addLayout(botoes)
        layout.addWidget(self.camera_label)
        layout.addWidget(self.progresso)
        layout.addWidget(self.status)
        self.botao_iniciar.clicked.connect(self.iniciar_cadastro)
        self.botao_cancelar.clicked.connect(self.cancelar_cadastro)
        self._atualizar_limites()

    def _atualizar_limites(self):
        self.config = carregar_configuracoes()
        self.quantidade = self.config["quantidade_cadastro"]
        self.intervalo = self.config["intervalo_cadastro"]
        self.progresso.setRange(0, self.quantidade)
        if self.engine is not None:
            self.engine.configurar_confianca(self.config["confianca_deteccao"])

    def preparar_recadastro(self, nome):
        self.parar_camera()
        self.modo_recadastro = True
        self.autorizar.setChecked(nome.strip().lower() in carregar_configuracoes()['pessoas_autorizadas'])
        self.nome.setText(nome)
        self.nome.setEnabled(False)
        self.progresso.setValue(0)
        self.status.setText(f"Pronto para recadastrar {nome.title()}.")

    def obter_instrucao(self):
        proporcao = self.contador / max(1, self.quantidade)
        if proporcao < 0.25:
            return "Olhe para frente"
        if proporcao < 0.45:
            return "Vire levemente para a esquerda"
        if proporcao < 0.65:
            return "Vire levemente para a direita"
        if proporcao < 0.85:
            return "Olhe levemente para cima"
        return "Olhe levemente para baixo"

    def iniciar_cadastro(self):
        if not self.pode_administrar():
            return
        self._atualizar_limites()
        try:
            self.nome_atual = normalizar_nome(self.nome.text())
        except ValueError as erro:
            self.status.setText(str(erro))
            return

        try:
            if self.engine is None:
                self.engine = FaceEngine(self.config["confianca_deteccao"])
        except (OSError, RuntimeError, cv2.error) as erro:
            self.status.setText(f"Não foi possível carregar os modelos: {erro}")
            return

        self.camera = abrir_camera(
            self.config["camera"], self.config["largura_camera"],
            self.config["altura_camera"], self.config["fps_camera"],
        )
        if self.camera is None:
            self.status.setText("Não foi possível abrir a câmera.")
            return

        self.embeddings = []
        self.contador = 0
        self.ultima_captura = 0.0
        self.progresso.setValue(0)
        self.cadastrando = True
        self.nome.setEnabled(False)
        self.botao_iniciar.setEnabled(False)
        self.botao_cancelar.setEnabled(True)
        self.timer.start(max(15, round(1000 / self.config["fps_camera"])))
        self.status.setText(f"{self.obter_instrucao()} — 0/{self.quantidade}")

    def atualizar_camera(self):
        if not self.cadastrando or self.camera is None:
            return
        sucesso, frame = self.camera.read()
        if not sucesso:
            self.status.setText("Falha ao capturar imagem.")
            return

        rostos = self.engine.detectar(frame)
        if len(rostos) == 1:
            rosto = rostos[0]
            x, y, w, h = (int(rosto[i]) for i in range(4))
            confianca = float(rosto[-1])
            agora = time.monotonic()
            if confianca >= 0.90 and agora - self.ultima_captura >= self.intervalo:
                try:
                    self.embeddings.append(self.engine.embedding(frame, rosto))
                    self.contador += 1
                    self.ultima_captura = agora
                    self.progresso.setValue(self.contador)
                except (ValueError, cv2.error):
                    pass
                if self.contador >= self.quantidade:
                    self.finalizar_cadastro()
                    return
            cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
            self.status.setText(f"{self.obter_instrucao()} — {self.contador}/{self.quantidade}")
        elif len(rostos) > 1:
            self.status.setText("Deixe apenas uma pessoa na câmera.")
        else:
            self.status.setText("Posicione o rosto na câmera.")
        self._mostrar_frame(frame)

    def finalizar_cadastro(self):
        if not self.pode_administrar():
            return
        self.parar_camera()
        try:
            perfil = FaceEngine.criar_perfil(self.embeddings)
            self.store.salvar_perfil(self.nome_atual, perfil)
            definir_autorizacao(self.nome_atual, self.autorizar.isChecked())
            self.camera_label.setText(f"✓\n\n{self.nome_atual.title()}\ncadastrado com sucesso!")
            self.status.setText("Cadastro concluído · " + ("Acesso autorizado" if self.autorizar.isChecked() else "Acesso bloqueado"))
        except (ValueError, RuntimeError, OSError) as erro:
            self.camera_label.setText("Não foi possível concluir o cadastro.")
            self.status.setText(str(erro))
        self._liberar_interface(limpar_nome=True)

    def cancelar_cadastro(self):
        self.parar_camera()
        self.embeddings.clear()
        self.camera_label.clear()
        self.camera_label.setText("Informe o nome e inicie o cadastro.")
        self.status.setText("Cadastro cancelado.")
        self.progresso.setValue(0)
        self._liberar_interface(limpar_nome=True)

    def _liberar_interface(self, limpar_nome=False):
        self.nome.setEnabled(True)
        self.botao_iniciar.setEnabled(True)
        self.botao_cancelar.setEnabled(False)
        self.modo_recadastro = False
        if limpar_nome:
            self.nome.clear()
            self.autorizar.setChecked(True)

    def parar_camera(self):
        self.cadastrando = False
        self.timer.stop()
        if self.camera is not None:
            self.camera.release()
            self.camera = None
        self.engine = None

    def _mostrar_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        altura, largura, canais = rgb.shape
        imagem = QImage(rgb.data, largura, altura, canais * largura, QImage.Format_RGB888).copy()
        self.camera_label.setPixmap(QPixmap.fromImage(imagem))
