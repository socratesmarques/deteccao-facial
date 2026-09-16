import os
import time
import shutil

import cv2
import numpy as np

from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QLineEdit,
    QProgressBar,
    QApplication
)

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QImage, QPixmap

from configuracoes import carregar_configuracoes


class PaginaCadastro(QWidget):

    def __init__(self):
        super().__init__()

        # =========================
        # CONFIGURAÇÕES PADRÃO
        # =========================

        self.CAMERA = "/dev/video2"

        self.ARQUIVO_PERFIS = "perfis.npz"

        self.PASTA_DADOS = "dados"
        self.PASTA_TEMPORARIA = "dados_temporarios"

        self.QUANTIDADE = 20
        self.INTERVALO = 0.7

        # =========================
        # ESTADO
        # =========================

        self.camera = None
        self.timer = None

        self.nome_atual = None
        self.pasta_atual = None
        self.pasta_temporaria_atual = None

        self.contador = 0
        self.ultima_captura = 0

        self.cadastrando = False
        self.modo_recadastro = False

        # =========================
        # CONFIGURAÇÕES SALVAS
        # =========================

        config = carregar_configuracoes()

        self.CAMERA = config.get(
            "camera",
            "/dev/video2"
        )

        confianca = config.get(
            "confianca_deteccao",
            0.80
        )

        # =========================
        # YUNET
        # =========================

        self.detector = cv2.FaceDetectorYN.create(
            "modelos/yunet.onnx",
            "",
            (640, 480),
            confianca,
            0.3,
            5000
        )

        # =========================
        # SFACE
        # =========================

        self.reconhecedor = (
            cv2.FaceRecognizerSF.create(
                "modelos/sface.onnx",
                ""
            )
        )

        # =========================
        # INTERFACE
        # =========================

        layout = QVBoxLayout(self)

        titulo = QLabel(
            "Cadastrar Pessoa"
        )

        titulo.setStyleSheet(
            "font-size: 28px; "
            "font-weight: bold;"
        )

        # =========================
        # NOME
        # =========================

        self.nome = QLineEdit()

        self.nome.setPlaceholderText(
            "Digite o nome da pessoa"
        )

        # =========================
        # BOTÕES
        # =========================

        self.botao_iniciar = QPushButton(
            "Iniciar cadastro"
        )

        self.botao_cancelar = QPushButton(
            "Cancelar"
        )

        self.botao_cancelar.setEnabled(
            False
        )

        botoes = QHBoxLayout()

        botoes.addWidget(
            self.botao_iniciar
        )

        botoes.addWidget(
            self.botao_cancelar
        )

        # =========================
        # CÂMERA
        # =========================

        self.camera_label = QLabel(
            "Informe o nome e inicie o cadastro."
        )

        self.camera_label.setAlignment(
            Qt.AlignCenter
        )

        self.camera_label.setMinimumSize(
            640,
            400
        )

        # =========================
        # PROGRESSO
        # =========================

        self.progresso = QProgressBar()

        self.progresso.setRange(
            0,
            self.QUANTIDADE
        )

        self.progresso.setValue(
            0
        )

        # =========================
        # STATUS
        # =========================

        self.status = QLabel(
            "Aguardando cadastro..."
        )

        self.status.setAlignment(
            Qt.AlignCenter
        )

        # =========================
        # LAYOUT
        # =========================

        layout.addWidget(
            titulo
        )

        layout.addSpacing(
            15
        )

        layout.addWidget(
            self.nome
        )

        layout.addLayout(
            botoes
        )

        layout.addSpacing(
            15
        )

        layout.addWidget(
            self.camera_label
        )

        layout.addWidget(
            self.progresso
        )

        layout.addWidget(
            self.status
        )

        # =========================
        # EVENTOS
        # =========================

        self.botao_iniciar.clicked.connect(
            self.iniciar_cadastro
        )

        self.botao_cancelar.clicked.connect(
            self.cancelar_cadastro
        )

    # =============================
    # PREPARAR RECADASTRO
    # =============================

    def preparar_recadastro(
        self,
        nome
    ):

        self.parar_camera()

        self.modo_recadastro = True

        self.nome.setText(
            nome
        )

        self.nome.setEnabled(
            False
        )

        self.progresso.setValue(
            0
        )

        self.camera_label.clear()

        self.camera_label.setStyleSheet(
            ""
        )

        self.camera_label.setText(
            "Clique em Iniciar cadastro."
        )

        self.status.setText(
            f"Pronto para recadastrar "
            f"{nome.title()}."
        )

    # =============================
    # INSTRUÇÃO DO ROSTO
    # =============================

    def obter_instrucao(self):

        if self.contador < 5:

            return (
                "Olhe para frente"
            )

        elif self.contador < 9:

            return (
                "Vire levemente para a esquerda"
            )

        elif self.contador < 13:

            return (
                "Vire levemente para a direita"
            )

        elif self.contador < 17:

            return (
                "Olhe levemente para cima"
            )

        else:

            return (
                "Olhe levemente para baixo"
            )

    # =============================
    # INICIAR CADASTRO
    # =============================

    def iniciar_cadastro(self):

        # =========================
        # CARREGAR CONFIGURAÇÕES
        # =========================

        config = carregar_configuracoes()

        self.CAMERA = config.get(
            "camera",
            "/dev/video2"
        )

        confianca = config.get(
            "confianca_deteccao",
            0.80
        )

        # Atualiza a confiança do YuNet
        self.detector.setScoreThreshold(
            confianca
        )

        # =========================
        # NOME
        # =========================

        nome = (
            self.nome
            .text()
            .strip()
            .lower()
        )

        if not nome:

            self.status.setText(
                "Digite um nome."
            )

            return

        self.nome_atual = nome

        # =========================
        # LIMPAR INTERFACE
        # =========================

        self.camera_label.clear()

        self.camera_label.setStyleSheet(
            ""
        )

        self.status.setText(
            "Iniciando câmera..."
        )

        # =========================
        # PASTA DEFINITIVA
        # =========================

        self.pasta_atual = os.path.join(
            self.PASTA_DADOS,
            nome
        )

        # =========================
        # PASTA TEMPORÁRIA
        # =========================

        self.pasta_temporaria_atual = (
            os.path.join(
                self.PASTA_TEMPORARIA,
                nome
            )
        )

        # Remove temporário antigo
        if os.path.exists(
            self.pasta_temporaria_atual
        ):

            shutil.rmtree(
                self.pasta_temporaria_atual
            )

        os.makedirs(
            self.pasta_temporaria_atual,
            exist_ok=True
        )

        # =========================
        # CONTADORES
        # =========================

        self.contador = 0
        self.ultima_captura = 0

        self.progresso.setValue(
            0
        )

        # =========================
        # ABRIR CÂMERA
        # =========================

        self.camera = cv2.VideoCapture(
            self.CAMERA,
            cv2.CAP_V4L2
        )

        if not self.camera.isOpened():

            self.status.setText(
                "Não foi possível abrir a câmera."
            )

            self.camera = None

            self.limpar_temporario()

            return

        # =========================
        # TIMER
        # =========================

        self.timer = QTimer(
            self
        )

        self.timer.timeout.connect(
            self.atualizar_camera
        )

        self.timer.start(
            33
        )

        self.cadastrando = True

        # =========================
        # INTERFACE
        # =========================

        self.nome.setEnabled(
            False
        )

        self.botao_iniciar.setEnabled(
            False
        )

        self.botao_cancelar.setEnabled(
            True
        )

        self.status.setText(
            f"{self.obter_instrucao()} — "
            f"0/{self.QUANTIDADE}"
        )

    # =============================
    # ATUALIZAR CÂMERA
    # =============================

    def atualizar_camera(self):

        if not self.cadastrando:
            return

        if self.camera is None:
            return

        sucesso, frame = (
            self.camera.read()
        )

        if not sucesso:
            return

        altura, largura = (
            frame.shape[:2]
        )

        # =========================
        # DETECÇÃO YUNET
        # =========================

        self.detector.setInputSize(
            (largura, altura)
        )

        _, rostos = (
            self.detector.detect(
                frame
            )
        )

        # =========================
        # UM ROSTO
        # =========================

        if (
            rostos is not None
            and len(rostos) == 1
        ):

            rosto = rostos[0]

            x = int(
                rosto[0]
            )

            y = int(
                rosto[1]
            )

            w = int(
                rosto[2]
            )

            h = int(
                rosto[3]
            )

            confianca = (
                rosto[-1]
            )

            instrucao = (
                self.obter_instrucao()
            )

            # =========================
            # RETÂNGULO
            # =========================

            cv2.rectangle(
                frame,
                (x, y),
                (x + w, y + h),
                (0, 255, 0),
                2
            )

            # =========================
            # CONFIANÇA
            # =========================

            cv2.putText(
                frame,
                f"Rosto {confianca:.2f}",
                (
                    x,
                    max(y - 10, 20)
                ),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.65,
                (0, 255, 0),
                2
            )

            # =========================
            # INSTRUÇÃO
            # =========================

            cv2.putText(
                frame,
                instrucao,
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2
            )

            self.status.setText(
                f"{instrucao} — "
                f"{self.contador}/"
                f"{self.QUANTIDADE}"
            )

            # =========================
            # CAPTURA
            # =========================

            agora = time.time()

            if (
                confianca >= 0.90
                and
                agora - self.ultima_captura
                >= self.INTERVALO
                and
                self.contador
                < self.QUANTIDADE
            ):

                rosto_alinhado = (
                    self.reconhecedor.alignCrop(
                        frame,
                        rosto
                    )
                )

                self.contador += 1

                caminho = os.path.join(
                    self.pasta_temporaria_atual,
                    f"rosto_{self.contador}.jpg"
                )

                salvou = cv2.imwrite(
                    caminho,
                    rosto_alinhado
                )

                if not salvou:

                    self.contador -= 1

                    self.status.setText(
                        "Erro ao salvar a foto."
                    )

                    return

                self.ultima_captura = (
                    agora
                )

                self.progresso.setValue(
                    self.contador
                )

                # =====================
                # TERMINOU
                # =====================

                if (
                    self.contador
                    >= self.QUANTIDADE
                ):

                    self.finalizar_cadastro()

                    return

                self.status.setText(
                    f"{self.obter_instrucao()} — "
                    f"{self.contador}/"
                    f"{self.QUANTIDADE}"
                )

        # =========================
        # MAIS DE UM ROSTO
        # =========================

        elif (
            rostos is not None
            and len(rostos) > 1
        ):

            self.status.setText(
                "Deixe apenas uma pessoa na câmera."
            )

            cv2.putText(
                frame,
                "Apenas uma pessoa",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2
            )

        # =========================
        # NENHUM ROSTO
        # =========================

        else:

            self.status.setText(
                "Posicione o rosto na câmera."
            )

            cv2.putText(
                frame,
                "Posicione o rosto",
                (20, 40),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.75,
                (255, 255, 255),
                2
            )

        # =========================
        # OPENCV -> QT
        # =========================

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

    # =============================
    # FINALIZAR CADASTRO
    # =============================

    def finalizar_cadastro(self):

        nome_final = (
            self.nome_atual
        )

        # =========================
        # DESLIGAR CÂMERA
        # =========================

        self.parar_camera()

        # Remove o último frame
        self.camera_label.clear()

        self.camera_label.setStyleSheet(
            """
            QLabel {
                font-size: 24px;
                font-weight: bold;
                padding: 40px;
            }
            """
        )

        self.camera_label.setText(
            "Processando cadastro..."
        )

        self.status.setText(
            "Gerando perfil facial..."
        )

        QApplication.processEvents()

        # =========================
        # GERAR PERFIL
        # =========================

        sucesso = (
            self.gerar_perfil()
        )

        # =========================
        # SUCESSO
        # =========================

        if sucesso:

            try:

                # Remove fotos antigas
                # somente após sucesso.
                if os.path.exists(
                    self.pasta_atual
                ):

                    shutil.rmtree(
                        self.pasta_atual
                    )

                # Move as novas fotos
                # para a pasta definitiva.
                shutil.move(
                    self.pasta_temporaria_atual,
                    self.pasta_atual
                )

                self.pasta_temporaria_atual = (
                    None
                )

                # =====================
                # TELA DE SUCESSO
                # =====================

                self.camera_label.clear()

                self.camera_label.setText(
                    f"✓\n\n"
                    f"{nome_final.title()}\n"
                    f"cadastrado com sucesso!"
                )

                self.camera_label.setStyleSheet(
                    """
                    QLabel {
                        font-size: 26px;
                        font-weight: bold;
                        padding: 40px;
                    }
                    """
                )

                self.status.setText(
                    "Cadastro concluído "
                    "com sucesso."
                )

            except Exception as erro:

                print(
                    "Erro ao mover fotos:",
                    erro
                )

                self.camera_label.clear()

                self.camera_label.setText(
                    "Erro ao finalizar cadastro."
                )

                self.status.setText(
                    "Perfil criado, mas ocorreu "
                    "um erro ao salvar as fotos."
                )

        # =========================
        # ERRO
        # =========================

        else:

            self.limpar_temporario()

            self.camera_label.clear()

            self.camera_label.setText(
                "Não foi possível concluir "
                "o cadastro."
            )

            self.status.setText(
                "Erro ao gerar perfil facial."
            )

        # =========================
        # LIBERAR INTERFACE
        # =========================

        self.nome.setEnabled(
            True
        )

        self.botao_iniciar.setEnabled(
            True
        )

        self.botao_cancelar.setEnabled(
            False
        )

        self.modo_recadastro = False

        self.nome.clear()

    # =============================
    # GERAR PERFIL
    # =============================

    def gerar_perfil(self):

        embeddings = []

        if (
            not self.pasta_temporaria_atual
            or
            not os.path.exists(
                self.pasta_temporaria_atual
            )
        ):

            return False

        # =========================
        # LER FOTOS
        # =========================

        for arquivo in sorted(
            os.listdir(
                self.pasta_temporaria_atual
            )
        ):

            if not arquivo.lower().endswith(
                (
                    ".jpg",
                    ".jpeg",
                    ".png"
                )
            ):

                continue

            caminho = os.path.join(
                self.pasta_temporaria_atual,
                arquivo
            )

            imagem = cv2.imread(
                caminho
            )

            if imagem is None:
                continue

            # =========================
            # EMBEDDING SFACE
            # =========================

            embedding = (
                self.reconhecedor.feature(
                    imagem
                ).flatten()
            )

            # =========================
            # NORMALIZAÇÃO
            # =========================

            norma = np.linalg.norm(
                embedding
            )

            if norma == 0:
                continue

            embedding = (
                embedding / norma
            )

            embeddings.append(
                embedding
            )

        # =========================
        # VALIDAR
        # =========================

        if len(embeddings) == 0:

            print(
                "Nenhum embedding válido."
            )

            return False

        # =========================
        # PERFIL MÉDIO
        # =========================

        perfil = np.mean(
            embeddings,
            axis=0
        )

        norma = np.linalg.norm(
            perfil
        )

        if norma == 0:
            return False

        perfil = (
            perfil / norma
        )

        # =========================
        # CARREGAR BANCO
        # =========================

        if os.path.exists(
            self.ARQUIVO_PERFIS
        ):

            dados = np.load(
                self.ARQUIVO_PERFIS
            )

            perfis = list(
                dados["perfis"]
            )

            nomes = [
                str(nome)
                for nome in dados["nomes"]
            ]

        else:

            perfis = []
            nomes = []

        # =========================
        # ATUALIZAR PERFIL
        # =========================

        if self.nome_atual in nomes:

            indice = nomes.index(
                self.nome_atual
            )

            perfis[indice] = (
                perfil
            )

            print(
                f"Perfil de "
                f"{self.nome_atual} "
                f"atualizado."
            )

        # =========================
        # NOVO PERFIL
        # =========================

        else:

            nomes.append(
                self.nome_atual
            )

            perfis.append(
                perfil
            )

            print(
                f"Perfil de "
                f"{self.nome_atual} "
                f"criado."
            )

        # =========================
        # SALVAR BANCO
        # =========================

        np.savez(
            self.ARQUIVO_PERFIS,

            perfis=np.array(
                perfis,
                dtype=np.float32
            ),

            nomes=np.array(
                nomes
            )
        )

        print(
            f"{len(embeddings)} "
            f"embeddings utilizados."
        )

        return True

    # =============================
    # CANCELAR CADASTRO
    # =============================

    def cancelar_cadastro(self):

        self.parar_camera()

        # Apaga apenas arquivos
        # temporários.
        self.limpar_temporario()

        # Remove último frame
        self.camera_label.clear()

        self.camera_label.setStyleSheet(
            ""
        )

        self.camera_label.setText(
            "Informe o nome e inicie o cadastro."
        )

        self.status.setText(
            "Cadastro cancelado."
        )

        self.nome.setEnabled(
            True
        )

        self.botao_iniciar.setEnabled(
            True
        )

        self.botao_cancelar.setEnabled(
            False
        )

        self.modo_recadastro = False

        self.nome.clear()

        self.progresso.setValue(
            0
        )

    # =============================
    # LIMPAR TEMPORÁRIO
    # =============================

    def limpar_temporario(self):

        if (
            self.pasta_temporaria_atual
            and
            os.path.exists(
                self.pasta_temporaria_atual
            )
        ):

            shutil.rmtree(
                self.pasta_temporaria_atual
            )

        self.pasta_temporaria_atual = (
            None
        )

    # =============================
    # PARAR CÂMERA
    # =============================

    def parar_camera(self):

        self.cadastrando = False

        if self.timer is not None:

            self.timer.stop()
            self.timer.deleteLater()
            self.timer = None

        if self.camera is not None:

            self.camera.release()
            self.camera = None