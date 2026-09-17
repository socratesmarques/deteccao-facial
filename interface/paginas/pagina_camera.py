from __future__ import annotations

import threading
import time

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from recognition_worker import RecognitionWorker
from configuracoes import carregar_configuracoes
from controle_acesso import ControleAcesso
from perfil_store import PerfilStore


class PaginaCamera(QWidget):
    resultado_porta = Signal(bool)

    def __init__(self):
        super().__init__()
        self.camera = None
        self.worker = None
        self.generation = None
        self.store = PerfilStore()
        self.controle_acesso = ControleAcesso()
        self.perfis, self.nomes = self.store.carregar()
        self.config = {}
        self.nome_confirmacao = None
        self.frames_confirmados = 0
        self.ultimo_acesso = 0.0
        self.abrindo_porta = False
        self.contador_frames = 0
        self.fps = 0.0
        self.tempo_frame = time.monotonic()

        layout = QVBoxLayout(self)
        titulo = QLabel("Reconhecimento Facial")
        titulo.setStyleSheet("font-size: 28px; font-weight: bold;")
        self.status_acesso = QLabel("Aguardando câmera...")
        self.status_acesso.setAlignment(Qt.AlignCenter)
        self.camera_label = QLabel("Câmera desligada")
        self.camera_label.setAlignment(Qt.AlignCenter)
        self.camera_label.setMinimumSize(640, 400)
        layout.addWidget(titulo)
        layout.addWidget(self.status_acesso)
        layout.addWidget(self.camera_label)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.atualizar_camera)
        self.resultado_porta.connect(self._mostrar_resultado_porta)
        self.carregar_configuracoes()

    def carregar_configuracoes(self):
        self.config = carregar_configuracoes()
        self.controle_acesso.configurar(
            self.config["porta_esp32"], self.config["baudrate_esp32"]
        )

    def carregar_perfis(self):
        try:
            self.perfis, self.nomes = self.store.carregar()
        except RuntimeError as erro:
            print(erro)
            self.perfis = np.empty((0, 128), dtype=np.float32)
            self.nomes = np.array([], dtype=str)

    def iniciar_camera(self):
        if self.worker is not None and self.worker.is_alive():
            self.status_acesso.setText("Câmera em uso; aguarde encerrar antes de reiniciar.")
            return
        self.carregar_configuracoes()
        self.carregar_perfis()
        self._reiniciar_confirmacao()
        self.generation = None
        self.fps = 0.0
        self.tempo_frame = time.monotonic()
        self.camera_label.setText("Iniciando câmera...")
        self.worker = RecognitionWorker(self.config, self.perfis, self.nomes)
        self.worker.start()
        self.timer.start(max(15, round(1000 / self.config["fps_camera"])))

    def parar_camera(self):
        self.timer.stop()
        self._reiniciar_confirmacao()
        self.camera_label.setText("Câmera desligada")
        if self.worker is not None:
            if not self.worker.stop():
                self.status_acesso.setText("Aguardando o driver liberar a câmera. Tente novamente.")
                return False
            self.worker = None
        return True

    def verificar_acesso(self, nome: str):
        nome = nome.strip().lower()
        autorizados = set(self.config["pessoas_autorizadas"])
        if nome == "desconhecido":
            self._reiniciar_confirmacao()
            self.status_acesso.setText("Pessoa não reconhecida")
            return
        if nome not in autorizados:
            self._reiniciar_confirmacao()
            self.status_acesso.setText(f"{nome.title()} — sem autorização")
            return

        if self.nome_confirmacao == nome:
            self.frames_confirmados += 1
        else:
            self.nome_confirmacao, self.frames_confirmados = nome, 1
        necessarios = self.config["frames_confirmacao"]
        self.status_acesso.setText(f"Verificando {nome.title()}... {self.frames_confirmados}/{necessarios}")
        if self.frames_confirmados < necessarios or self.abrindo_porta:
            return

        agora = time.monotonic()
        restante = self.config["cooldown_acesso"] - (agora - self.ultimo_acesso)
        if restante > 0:
            self.status_acesso.setText(f"{nome.title()} autorizado — aguarde {int(restante) + 1}s")
            return

        self.abrindo_porta = True
        self.status_acesso.setText("Comunicando com o ESP32...")
        threading.Thread(target=self._abrir_porta, daemon=True).start()
        self._reiniciar_confirmacao()

    def _abrir_porta(self):
        self.resultado_porta.emit(self.controle_acesso.abrir())

    def _mostrar_resultado_porta(self, sucesso: bool):
        self.abrindo_porta = False
        if sucesso:
            self.ultimo_acesso = time.monotonic()
            self.status_acesso.setText("Acesso liberado")
        else:
            self.status_acesso.setText("Falha na comunicação com o ESP32")

    def _reiniciar_confirmacao(self):
        self.nome_confirmacao = None
        self.frames_confirmados = 0

    def atualizar_camera(self):
        if self.worker is None:
            return
        result = self.worker.take()
        agora = time.monotonic()
        if result is None:
            if agora - self.tempo_frame > 1.0:
                self._reiniciar_confirmacao()
                self.camera_label.setText("Aguardando novos quadros da câmera...")
            return
        if result['error']:
            self._reiniciar_confirmacao()
            self.camera_label.setText("Câmera indisponível")
            self.status_acesso.setText(result['error'])
            self.timer.stop()
            return
        if agora - result['captured'] > 1.0:
            self._reiniciar_confirmacao()
            self.camera_label.setText("Processamento lento: quadro descartado")
            return
        if self.generation != result['generation']:
            self._reiniciar_confirmacao()
            self.generation = result['generation']
        if not result['visible']:
            self._reiniciar_confirmacao()
            self.status_acesso.setText("Aguardando rosto selecionado...")
        elif result['fresh']:
            self.verificar_acesso(result['name'])
        delta = agora - self.tempo_frame
        if delta > 0:
            atual = 1.0 / delta
            self.fps = atual if self.fps == 0 else self.fps * 0.9 + atual * 0.1
        self.tempo_frame = agora
        frame = result['frame']
        if self.config["mostrar_fps"]:
            cv2.putText(frame, f"FPS: {self.fps:.1f}", (20, 35),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.65, (0, 255, 0), 2)
        self._mostrar_frame(frame)

    def _mostrar_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        altura, largura, canais = rgb.shape
        imagem = QImage(rgb.data, largura, altura, canais * largura, QImage.Format_RGB888).copy()
        pixmap = QPixmap.fromImage(imagem).scaled(
            self.camera_label.size(), Qt.KeepAspectRatio, Qt.FastTransformation
        )
        self.camera_label.setPixmap(pixmap)

    def closeEvent(self, event):
        self.parar_camera()
        self.controle_acesso.desconectar()
        event.accept()
