from __future__ import annotations

import threading
import time

import cv2
import numpy as np
from PySide6.QtCore import Qt, QTimer, Signal
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QButtonGroup, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from interface.camera_view import CameraStatus, CameraView
from access_logger import AccessLogger
from recognition_worker import RecognitionWorker
from configuracoes import carregar_configuracoes
from controle_acesso import ControleAcesso
from perfil_store import PerfilStore
from frame_variation import FrameVariation
from anti_spoof import AntiSpoofWindow


class PaginaCamera(QWidget):
    resultado_porta = Signal(bool, str, str)

    def __init__(self):
        super().__init__()
        self.worker = None
        self.generation = None
        self.encontro = None
        self.observacoes_vistas = 0
        self.variacao_atual = None
        self.antispoof_atual = None
        self.variacao_base = 0
        self.store = PerfilStore()
        self.controle_acesso = ControleAcesso()
        self.logger = AccessLogger()
        self.carregar_perfis()
        self.config = {}
        self.nome_confirmacao = None
        self.frames_confirmados = 0
        self.ultimo_acesso = float('-inf')
        self.ultimos_acessos = {}
        self.abrindo_porta = False
        self.nome_acionamento = None
        self.antispoof_acionamento = None
        self.feedback_ate = 0.0
        self.fps = 0.0
        self.tempo_frame = time.monotonic()
        self.ultima_decisao_logada = None
        self.ultima_decisao_em = 0.0
        self.movimento = 'ENTRADA'
        self.acesso_registrado = None
        self.status_registrado = ''
        self.ausente_desde = None

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        self.camera_label = CameraView()
        layout.addWidget(self.camera_label, 1)
        painel = QWidget()
        feedback = QVBoxLayout(painel)
        feedback.setContentsMargins(18, 8, 18, 8)
        feedback.setSpacing(4)
        controles = QHBoxLayout()
        controles.addWidget(QLabel('Registrar:'))
        self.sentidos = QButtonGroup(self)
        self.botao_entrada = QPushButton('Entrada')
        self.botao_saida = QPushButton('Saída')
        for botao, sentido in ((self.botao_entrada, 'ENTRADA'), (self.botao_saida, 'SAIDA')):
            botao.setCheckable(True)
            botao.setStyleSheet('QPushButton { padding: 5px 16px; } QPushButton:checked { background: #236bda; color: white; }')
            botao.clicked.connect(lambda checked=False, valor=sentido: self.selecionar_movimento(valor))
            self.sentidos.addButton(botao)
            controles.addWidget(botao)
        controles.addStretch()
        self.botao_entrada.setChecked(True)
        feedback.addLayout(controles)
        self.status_acesso = CameraStatus()
        self.instrucao = QLabel('Escolha Entrada ou Saída e olhe para a câmera')
        self.instrucao.setObjectName('rodape')
        self.instrucao.setAlignment(Qt.AlignCenter)
        self.instrucao.setWordWrap(True)
        feedback.addWidget(self.status_acesso)
        feedback.addWidget(self.instrucao)
        layout.addWidget(painel)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.atualizar_camera)
        self.resultado_porta.connect(self._mostrar_resultado_porta)
        self.carregar_configuracoes()

    def selecionar_movimento(self, movimento):
        if self.abrindo_porta or movimento == self.movimento:
            return
        self.movimento = movimento
        self.variacao_atual = None
        self.antispoof_atual = None
        self.variacao_base = self.observacoes_vistas
        self.botao_entrada.setChecked(movimento == 'ENTRADA')
        self.botao_saida.setChecked(movimento == 'SAIDA')
        self._reiniciar_confirmacao()
        self.acesso_registrado = None
        self.feedback_ate = 0.0
        self.status_acesso.setText('Olhe para a câmera para confirmar ' + ('entrada' if movimento == 'ENTRADA' else 'saída'))
        # observacoes_vistas is retained: changing direction needs NEW inferences.

    def carregar_configuracoes(self):
        self.config = carregar_configuracoes()
        self.controle_acesso.configurar(self.config['gpio_chip'], self.config['gpio_linha_rele'],
                                       self.config['gpio_ativo_alto'], self.config['tempo_acionamento_rele'])

    def carregar_perfis(self):
        try:
            self.perfis, self.nomes = self.store.carregar()
        except RuntimeError as erro:
            print(erro)
            self.perfis, self.nomes = np.empty((0, 128), dtype=np.float32), np.array([], dtype=str)

    def iniciar_camera(self):
        if self.worker is not None and self.worker.is_alive():
            self.status_acesso.setText('Câmera em uso; aguarde encerrar antes de reiniciar.')
            return
        self.carregar_configuracoes()
        self.carregar_perfis()
        self._reiniciar_confirmacao()
        self.generation, self.observacoes_vistas = None, 0
        self.variacao_atual, self.variacao_base = None, 0
        self.antispoof_atual = None
        self.encontro = None
        self.acesso_registrado, self.ausente_desde = None, None
        self.feedback_ate, self.fps, self.tempo_frame = 0.0, 0.0, time.monotonic()
        self.camera_label.setText('Iniciando câmera...')
        self.status_acesso.setText('Preparando reconhecimento...')
        if not len(self.perfis):
            hint = 'Nenhuma pessoa cadastrada · Abra Admin → Cadastrar pessoa'
        elif not self.config['pessoas_autorizadas']:
            hint = 'Nenhuma pessoa autorizada · Abra Admin → Pessoas cadastradas → Autorizar'
        else:
            hint = 'Escolha Entrada ou Saída · ' + ('Relé habilitado' if self.config['rele_ativo'] else 'Sem relé')
        self.instrucao_padrao = hint
        self.instrucao.setText(hint)
        self.worker = RecognitionWorker(self.config, self.perfis, self.nomes)
        self.worker.start()
        self.timer.start(max(15, round(1000 / self.config['fps_camera'])))

    def parar_camera(self):
        self.timer.stop()
        self._reiniciar_confirmacao()
        self.camera_label.setText('Câmera desligada')
        if self.worker is not None:
            if not self.worker.stop():
                self.status_acesso.setText('Aguardando o driver liberar a câmera. Tente novamente.')
                return False
            self.worker = None
        return True

    def _gravar_log(self, nome, decisao, detalhe, movimento):
        try:
            self.logger.registrar(nome, decisao, detalhe, movimento)
            return True
        except (OSError, ValueError) as erro:
            self.status_acesso.setText(f'{self.status_acesso.text()} · ERRO ao salvar log: {erro}')
            return False

    def _registrar_decisao(self, nome, decisao, detalhe=''):
        chave, agora = (nome.strip().lower(), decisao, self.movimento), time.monotonic()
        if chave == self.ultima_decisao_logada and agora - self.ultima_decisao_em < 3:
            return
        if self._gravar_log(nome, decisao, detalhe, self.movimento):
            self.ultima_decisao_logada, self.ultima_decisao_em = chave, agora

    def _conferir_variacao(self, nome):
        prova = self.variacao_atual or {}
        amostras = prova.get('count', 0)
        inicio = prova.get('first_observation', 0)
        horario = prova.get('sampled_at')
        if (amostras < FrameVariation.FRAMES or inicio <= self.variacao_base
                or horario is None or not 0 <= time.monotonic() - horario <= FrameVariation.MAX_GAP):
            contagem = min(amostras, FrameVariation.FRAMES) if inicio > self.variacao_base else 0
            self.status_acesso.setText(f'{nome.title()} — CONFERINDO IMAGEM {contagem}/5')
            return False
        if not prova.get('different', False):
            self.status_acesso.setText(f'{nome.title()} — BLOQUEADO · SEM VARIAÇÃO NO ROSTO')
            self._registrar_decisao(nome, 'BLOQUEADO', 'Cinco amostras sem variação visual suficiente no rosto')
            return False
        return True

    def _conferir_antispoof(self, nome):
        prova = self.antispoof_atual or {}
        state = prova.get('state', 'pending')
        horario = prova.get('sampled_at')
        if state == 'error':
            self.status_acesso.setText(f'{nome.title()} — ERRO NA VERIFICAÇÃO')
            self.instrucao.setText('Verificação indisponível. Procure o administrador.')
            self._registrar_decisao(nome, 'ERRO', prova.get('reason', 'Anti-spoofing indisponível'))
            return False
        if (horario is None or not 0 <= time.monotonic()-horario <= AntiSpoofWindow.MAX_GAP
                or prova.get('first_observation', 0) <= self.variacao_base):
            self.status_acesso.setText(f'{nome.title()} — VERIFICANDO PRESENÇA 0/5')
            return False
        if state in ('spoof', 'uncertain'):
            message = 'SUSPEITA DE FOTO/TELA' if state == 'spoof' else 'VERIFICAÇÃO INCONCLUSIVA'
            self.status_acesso.setText(f'{nome.title()} — BLOQUEADO · {message}')
            self.instrucao.setText(prova.get('reason', 'Ajuste a iluminação e o enquadramento.'))
            score = prova.get('score')
            detalhe = f"Anti-spoofing {state}; score={score}; {prova.get('reason', '')}"
            self._registrar_decisao(nome, 'BLOQUEADO', detalhe)
            return False
        score = prova.get('score')
        if (state != 'live' or prova.get('count', 0) < AntiSpoofWindow.REQUIRED
                or score is None or not self.config.get('limiar_antispoof', .8) <= score <= 1):
            self.status_acesso.setText(f"{nome.title()} — VERIFICANDO PRESENÇA {min(prova.get('count', 0), 5)}/5")
            return False
        self.instrucao.setText(getattr(self, 'instrucao_padrao', 'Escolha Entrada ou Saída e olhe para a câmera'))
        return True

    def verificar_acesso(self, nome, novas_confirmacoes=1):
        original = nome.strip() or 'Desconhecido'
        nome = original.lower()
        if nome == 'desconhecido':
            self._reiniciar_confirmacao()
            self.status_acesso.setText('Desconhecido — BLOQUEADO')
            self._registrar_decisao('Desconhecido', 'BLOQUEADO', 'Rosto não reconhecido')
            return
        if nome not in self.config['pessoas_autorizadas']:
            self._reiniciar_confirmacao()
            self.status_acesso.setText(f'{original.title()} — SEM AUTORIZAÇÃO')
            self._registrar_decisao(original, 'BLOQUEADO', 'Perfil cadastrado sem autorização; autorize no painel Pessoas')
            return
        if self.nome_confirmacao == nome:
            self.frames_confirmados += novas_confirmacoes
        else:
            self.nome_confirmacao, self.frames_confirmados = nome, novas_confirmacoes
        if not self._conferir_antispoof(original):
            return
        if not self._conferir_variacao(original):
            return
        if self.acesso_registrado == (nome, self.movimento):
            self.status_acesso.setText(self.status_registrado)
            return
        if self.frames_confirmados < self.config['frames_confirmacao']:
            self.status_acesso.setText(f'{original.title()} — CONFIRMANDO {self.frames_confirmados}/{self.config["frames_confirmacao"]}')
            return
        if self.abrindo_porta:
            return
        agora = time.monotonic()
        ultimo = self.ultimo_acesso if self.config['rele_ativo'] else self.ultimos_acessos.get((nome, self.movimento), float('-inf'))
        falta = self.config['cooldown_acesso'] - (agora - ultimo)
        if falta > 0:
            self.status_acesso.setText(f'{original.title()} — AGUARDE {int(falta)+1}s')
            return
        if not self.config['rele_ativo']:
            self._concluir_liberacao(original, self.movimento, 'Rosto confirmado; modo sem relé')
            return
        self.status_acesso.setText(f'{original.title()} — ACIONANDO RELÉ')
        self.abrindo_porta, self.nome_acionamento = True, original
        self.antispoof_acionamento = dict(self.antispoof_atual or {})
        self.botao_entrada.setEnabled(False); self.botao_saida.setEnabled(False)
        threading.Thread(target=self._abrir_porta, args=(original, self.movimento), daemon=True).start()
        self._reiniciar_confirmacao()

    def _concluir_liberacao(self, nome, movimento, detalhe, evidence=None):
        self.ultimo_acesso = time.monotonic()
        self.ultimos_acessos[(nome.lower(), movimento)] = self.ultimo_acesso
        self.feedback_ate = self.ultimo_acesso + 2.5
        self.acesso_registrado = (nome.lower(), movimento)
        sentido = 'ENTRADA' if movimento == 'ENTRADA' else 'SAÍDA'
        self.status_acesso.setText(f'{nome.title()} — LIBERADO · {sentido}')
        evidence = evidence if evidence is not None else self.antispoof_atual
        if evidence and evidence.get('state') == 'live':
            detalhe += f"; anti-spoofing aprovado em 5 amostras, score mínimo={evidence.get('score')}"
        self._gravar_log(nome, 'LIBERADO', detalhe, movimento)
        self.status_registrado = self.status_acesso.text()
        self._reiniciar_confirmacao()

    def _abrir_porta(self, nome, movimento):
        self.resultado_porta.emit(self.controle_acesso.abrir(), nome, movimento)

    def _mostrar_resultado_porta(self, sucesso, nome, movimento=None):
        movimento = movimento or self.movimento
        self.abrindo_porta = False
        self.botao_entrada.setEnabled(True); self.botao_saida.setEnabled(True)
        self.feedback_ate = time.monotonic() + 2.5
        if sucesso:
            self._concluir_liberacao(nome, movimento, 'Rosto confirmado; pulso GPIO concluído', self.antispoof_acionamento)
        else:
            self.status_acesso.setText(f'{nome.title()} — ERRO NO RELÉ')
            self._gravar_log(nome, 'ERRO', self.controle_acesso.ultimo_erro or 'Falha ao acionar o relé', movimento)
        self.nome_acionamento = None
        self.antispoof_acionamento = None

    def _reiniciar_confirmacao(self):
        self.nome_confirmacao, self.frames_confirmados = None, 0

    def atualizar_camera(self):
        if self.worker is None:
            return
        result, agora = self.worker.take(), time.monotonic()
        if result is None:
            if agora - self.tempo_frame > 1:
                self._reiniciar_confirmacao()
                self.variacao_atual = None
                self.antispoof_atual = None
                self.variacao_base = self.observacoes_vistas
                self.camera_label.setText('Aguardando novos quadros da câmera...')
                self.status_acesso.setText('Câmera sem novos quadros — aguardando')
            return
        if result['error']:
            self._reiniciar_confirmacao()
            self.variacao_atual = None
            self.antispoof_atual = None
            self.camera_label.setText('Câmera indisponível')
            self.status_acesso.setText(result['error'])
            self.timer.stop()
            return
        if agora - result['captured'] > 1:
            self._reiniciar_confirmacao()
            self.generation = result.get('generation', self.generation)
            self.observacoes_vistas = result.get('observations', self.observacoes_vistas)
            self.variacao_atual = None
            self.antispoof_atual = None
            self.variacao_base = self.observacoes_vistas
            self.camera_label.setText('Processamento lento: quadro descartado')
            self.status_acesso.setText('Aguardando imagem atualizada')
            return
        encontro = result.get('encounter')
        if encontro is not None and encontro != self.encontro:
            self.acesso_registrado = None
            self.encontro = encontro
        if self.generation != result['generation']:
            self._reiniciar_confirmacao()
            self.generation, self.observacoes_vistas = result['generation'], 0
            self.variacao_base = 0
        self.variacao_atual = result.get('variation')
        self.antispoof_atual = result.get('antispoof')
        # Count actual inferences, even if their individual preview frames were replaced.
        observacoes = result.get('observations')
        novas = max(0, observacoes - self.observacoes_vistas) if observacoes is not None else int(result['fresh'])
        if observacoes is not None:
            self.observacoes_vistas = observacoes
        if not result['visible']:
            self._reiniciar_confirmacao()
            if self.ausente_desde is None:
                self.ausente_desde = agora
            if agora - self.ausente_desde >= 0.7:
                self.acesso_registrado = None
            self.status_acesso.setText('Aguardando rosto...')
        else:
            self.ausente_desde = None
            if self.abrindo_porta:
                self.status_acesso.setText(f'{self.nome_acionamento.title()} — ACIONANDO RELÉ')
            elif self.acesso_registrado == (result['name'].strip().lower(), self.movimento):
                if self._conferir_antispoof(result['name']) and self._conferir_variacao(result['name']):
                    self.status_acesso.setText(self.status_registrado)
            elif novas:
                if novas == 1:
                    self.verificar_acesso(result['name'])
                else:
                    self.verificar_acesso(result['name'], novas)
        delta = agora - self.tempo_frame
        if delta > 0:
            atual = 1 / delta
            self.fps = atual if self.fps == 0 else self.fps * 0.9 + atual * 0.1
        self.tempo_frame = agora
        self.camera_label.set_fps(self.fps if self.config['mostrar_fps'] else None)
        self.camera_label.set_face_box(result.get('face_box'))
        self._mostrar_frame(result['frame'])

    def _mostrar_frame(self, frame):
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        altura, largura, canais = rgb.shape
        imagem = QImage(rgb.data, largura, altura, canais * largura, QImage.Format_RGB888).copy()
        self.camera_label.setPixmap(QPixmap.fromImage(imagem))

    def closeEvent(self, event):
        self.parar_camera()
        self.controle_acesso.desconectar()
        event.accept()
