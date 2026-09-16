import os
import time

import cv2
import numpy as np

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QLabel
)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

from configuracoes import carregar_configuracoes
from controle_acesso import ControleAcesso


class PaginaCamera(QWidget):
    def __init__(self):
        super().__init__()

        self.ARQUIVO_PERFIS = "perfis.npz"

        # =====================================================
        # CONFIGURAÇÕES
        # =====================================================

        config = carregar_configuracoes()

        self.CAMERA = config.get(
            "camera",
            "/dev/video2"
        )

        self.LIMIAR = config.get(
            "limiar_reconhecimento",
            0.45
        )

        self.CONFIANCA_DETECCAO = config.get(
            "confianca_deteccao",
            0.80
        )

        self.MOSTRAR_FPS = config.get(
            "mostrar_fps",
            False
        )

        # =====================================================
        # CÂMERA
        # =====================================================

        self.camera = None

        # =====================================================
        # FPS
        # =====================================================

        self.fps = 0
        self.tempo_frame_anterior = time.time()

        # =====================================================
        # CONTROLE DE ACESSO
        # =====================================================

        self.controle_acesso = ControleAcesso(
            porta="/dev/ttyACM0",
            baudrate=115200
        )

        # Pessoas que podem abrir a porta.
        # Os nomes devem ser iguais aos cadastrados.
        self.pessoas_autorizadas = {
            "socrates"
        }

        # Quantos frames seguidos são necessários
        self.frames_necessarios = 5

        self.nome_confirmacao = None
        self.frames_confirmados = 0

        # Tempo mínimo entre duas aberturas
        self.cooldown_acesso = 10

        self.ultimo_acesso = 0

        # =====================================================
        # INTERFACE
        # =====================================================

        layout = QVBoxLayout(self)

        titulo = QLabel(
            "Reconhecimento Facial"
        )

        titulo.setStyleSheet(
            "font-size: 28px; "
            "font-weight: bold;"
        )

        self.status_acesso = QLabel(
            "Controle de acesso ativo"
        )

        self.status_acesso.setAlignment(
            Qt.AlignCenter
        )

        self.camera_label = QLabel(
            "Câmera desligada"
        )

        self.camera_label.setAlignment(
            Qt.AlignCenter
        )

        self.camera_label.setMinimumSize(
            700,
            500
        )

        layout.addWidget(titulo)
        layout.addWidget(self.status_acesso)
        layout.addWidget(self.camera_label)

        # =====================================================
        # YUNET
        # =====================================================

        self.detector = cv2.FaceDetectorYN.create(
            "modelos/yunet.onnx",
            "",
            (640, 480),
            self.CONFIANCA_DETECCAO,
            0.3,
            5000
        )

        # =====================================================
        # SFACE
        # =====================================================

        self.reconhecedor = (
            cv2.FaceRecognizerSF.create(
                "modelos/sface.onnx",
                ""
            )
        )

        # =====================================================
        # PERFIS
        # =====================================================

        self.perfis = np.array([])
        self.nomes = np.array([])

        self.carregar_perfis()

        # =====================================================
        # TIMER
        # =====================================================

        self.timer = QTimer(self)

        self.timer.timeout.connect(
            self.atualizar_camera
        )

    # =========================================================
    # CONFIGURAÇÕES
    # =========================================================

    def carregar_configuracoes(self):
        config = carregar_configuracoes()

        self.CAMERA = config.get(
            "camera",
            "/dev/video2"
        )

        self.LIMIAR = config.get(
            "limiar_reconhecimento",
            0.45
        )

        self.CONFIANCA_DETECCAO = config.get(
            "confianca_deteccao",
            0.80
        )

        self.MOSTRAR_FPS = config.get(
            "mostrar_fps",
            False
        )

        self.detector.setScoreThreshold(
            self.CONFIANCA_DETECCAO
        )

    # =========================================================
    # PERFIS
    # =========================================================

    def carregar_perfis(self):
        if not os.path.exists(
            self.ARQUIVO_PERFIS
        ):
            self.perfis = np.array([])
            self.nomes = np.array([])

            print(
                "Nenhum perfil encontrado."
            )

            return

        try:
            dados = np.load(
                self.ARQUIVO_PERFIS
            )

            self.perfis = dados["perfis"]
            self.nomes = dados["nomes"]

            print(
                f"{len(self.nomes)} "
                "pessoa(s) carregada(s)."
            )

        except Exception as erro:
            print(
                "Erro ao carregar perfis:",
                erro
            )

            self.perfis = np.array([])
            self.nomes = np.array([])

    # =========================================================
    # CÂMERA
    # =========================================================

    def iniciar_camera(self):
        self.carregar_configuracoes()

        if (
            self.camera is not None
            and self.camera.isOpened()
        ):
            return

        self.camera_label.clear()

        self.camera_label.setText(
            "Iniciando câmera..."
        )

        self.camera = cv2.VideoCapture(
            self.CAMERA,
            cv2.CAP_V4L2
        )

        if not self.camera.isOpened():
            self.camera_label.setText(
                "Não foi possível abrir "
                f"a câmera {self.CAMERA}."
            )

            self.camera = None
            return

        # Reinicia FPS
        self.fps = 0
        self.tempo_frame_anterior = (
            time.time()
        )

        # Reinicia confirmação facial
        self.nome_confirmacao = None
        self.frames_confirmados = 0

        self.status_acesso.setText(
            "Controle de acesso ativo"
        )

        self.timer.start(33)

    def parar_camera(self):
        self.timer.stop()

        if self.camera is not None:
            self.camera.release()
            self.camera = None

        self.nome_confirmacao = None
        self.frames_confirmados = 0

        self.camera_label.clear()

        self.camera_label.setText(
            "Câmera desligada"
        )

    # =========================================================
    # RECONHECIMENTO
    # =========================================================

    def reconhecer_rosto(
        self,
        frame,
        rosto
    ):
        if len(self.perfis) == 0:
            return (
                "Desconhecido",
                0
            )

        try:
            rosto_alinhado = (
                self.reconhecedor.alignCrop(
                    frame,
                    rosto
                )
            )

            embedding = (
                self.reconhecedor.feature(
                    rosto_alinhado
                ).flatten()
            )

            norma = np.linalg.norm(
                embedding
            )

            if norma == 0:
                return (
                    "Desconhecido",
                    0
                )

            embedding = (
                embedding / norma
            )

            melhor_nome = "Desconhecido"
            melhor_score = -1

            for perfil, nome in zip(
                self.perfis,
                self.nomes
            ):
                score = (
                    self.reconhecedor.match(
                        embedding,
                        perfil,
                        cv2.FaceRecognizerSF_FR_COSINE
                    )
                )

                if score > melhor_score:
                    melhor_score = score
                    melhor_nome = str(nome)

            if melhor_score < self.LIMIAR:
                melhor_nome = (
                    "Desconhecido"
                )

            return (
                melhor_nome,
                melhor_score
            )

        except Exception as erro:
            print(
                "Erro no reconhecimento:",
                erro
            )

            return (
                "Desconhecido",
                0
            )

    # =========================================================
    # CONTROLE DE ACESSO
    # =========================================================

    def verificar_acesso(self, nome):
        nome_normalizado = (
            nome.strip().lower()
        )

        # Pessoa desconhecida
        if nome_normalizado == "desconhecido":
            self.nome_confirmacao = None
            self.frames_confirmados = 0

            self.status_acesso.setText(
                "Pessoa não reconhecida"
            )

            return

        # Pessoa cadastrada, mas sem autorização
        if (
            nome_normalizado
            not in self.pessoas_autorizadas
        ):
            self.nome_confirmacao = None
            self.frames_confirmados = 0

            self.status_acesso.setText(
                f"{nome.title()} - "
                "sem autorização"
            )

            return

        # Mesmo rosto do frame anterior
        if (
            self.nome_confirmacao
            == nome_normalizado
        ):
            self.frames_confirmados += 1

        else:
            self.nome_confirmacao = (
                nome_normalizado
            )

            self.frames_confirmados = 1

        self.status_acesso.setText(
            f"Verificando {nome.title()}... "
            f"{self.frames_confirmados}/"
            f"{self.frames_necessarios}"
        )

        # Ainda não confirmou frames suficientes
        if (
            self.frames_confirmados
            < self.frames_necessarios
        ):
            return

        agora = time.time()

        # Verifica cooldown
        if (
            agora - self.ultimo_acesso
            < self.cooldown_acesso
        ):
            restante = int(
                self.cooldown_acesso
                - (
                    agora
                    - self.ultimo_acesso
                )
            )

            self.status_acesso.setText(
                f"{nome.title()} autorizado - "
                f"aguarde {restante}s"
            )

            return

        # =====================================================
        # ACESSO LIBERADO
        # =====================================================

        sucesso = (
            self.controle_acesso.abrir()
        )

        if sucesso:
            self.ultimo_acesso = agora

            self.status_acesso.setText(
                f"Acesso liberado: "
                f"{nome.title()}"
            )

            print(
                "Acesso liberado para:",
                nome
            )

        else:
            self.status_acesso.setText(
                "Falha na comunicação "
                "com o ESP32"
            )

            print(
                "Falha ao enviar comando "
                "para o ESP32."
            )

        # Reinicia confirmação
        self.nome_confirmacao = None
        self.frames_confirmados = 0

    # =========================================================
    # ATUALIZAÇÃO DA CÂMERA
    # =========================================================

    def atualizar_camera(self):
        if self.camera is None:
            return

        sucesso, frame = (
            self.camera.read()
        )

        if not sucesso:
            return

        # =====================================================
        # FPS
        # =====================================================

        agora = time.time()

        tempo_decorrido = (
            agora
            - self.tempo_frame_anterior
        )

        if tempo_decorrido > 0:
            fps_instantaneo = (
                1 / tempo_decorrido
            )

            if self.fps == 0:
                self.fps = (
                    fps_instantaneo
                )

            else:
                self.fps = (
                    self.fps * 0.9
                    + fps_instantaneo * 0.1
                )

        self.tempo_frame_anterior = agora

        # =====================================================
        # DETECÇÃO
        # =====================================================

        altura, largura = (
            frame.shape[:2]
        )

        self.detector.setInputSize(
            (largura, altura)
        )

        _, rostos = (
            self.detector.detect(frame)
        )

        # Guarda os nomes reconhecidos
        nomes_frame = []

        if rostos is not None:
            for rosto in rostos:
                x = int(rosto[0])
                y = int(rosto[1])
                w = int(rosto[2])
                h = int(rosto[3])

                nome, score = (
                    self.reconhecer_rosto(
                        frame,
                        rosto
                    )
                )

                nomes_frame.append(nome)

                if nome == "Desconhecido":
                    cor = (
                        0,
                        0,
                        255
                    )

                else:
                    cor = (
                        0,
                        255,
                        0
                    )

                cv2.rectangle(
                    frame,
                    (x, y),
                    (
                        x + w,
                        y + h
                    ),
                    cor,
                    2
                )

                texto = (
                    f"{nome} "
                    f"{score:.2f}"
                )

                cv2.putText(
                    frame,
                    texto,
                    (
                        x,
                        max(
                            y - 10,
                            20
                        )
                    ),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.7,
                    cor,
                    2
                )

        # =====================================================
        # VERIFICAÇÃO DE ACESSO
        # =====================================================

        if len(nomes_frame) == 1:
            self.verificar_acesso(
                nomes_frame[0]
            )

        elif len(nomes_frame) == 0:
            self.nome_confirmacao = None
            self.frames_confirmados = 0

            self.status_acesso.setText(
                "Aguardando pessoa..."
            )

        else:
            # Por segurança, não abre com
            # várias faces simultaneamente.
            self.nome_confirmacao = None
            self.frames_confirmados = 0

            self.status_acesso.setText(
                "Mais de uma pessoa detectada"
            )

        # =====================================================
        # FPS NA TELA
        # =====================================================

        if self.MOSTRAR_FPS:
            cv2.putText(
                frame,
                f"FPS: {self.fps:.1f}",
                (20, 35),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (0, 255, 0),
                2
            )

        # =====================================================
        # OPENCV -> PYSIDE
        # =====================================================

        frame_rgb = cv2.cvtColor(
            frame,
            cv2.COLOR_BGR2RGB
        )

        altura, largura, canais = (
            frame_rgb.shape
        )

        imagem = QImage(
            frame_rgb.data,
            largura,
            altura,
            canais * largura,
            QImage.Format_RGB888
        )

        imagem = imagem.copy()

        pixmap = QPixmap.fromImage(
            imagem
        )

        pixmap = pixmap.scaled(
            self.camera_label.size(),
            Qt.KeepAspectRatio,
            Qt.SmoothTransformation
        )

        self.camera_label.setPixmap(
            pixmap
        )

    # =========================================================
    # FECHAR
    # =========================================================

    def closeEvent(self, event):
        self.parar_camera()

        self.controle_acesso.desconectar()

        event.accept()