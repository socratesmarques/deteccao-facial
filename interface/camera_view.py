"""Visualização leve: mantém a imagem inteira e redesenha ao redimensionar."""
from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen, QPixmap
from PySide6.QtWidgets import QLabel, QSizePolicy, QWidget


class CameraView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._imagem = QPixmap()
        self._mensagem = "Iniciando câmera…"
        self._fps = None
        self._face_box = None
        self.setMinimumSize(240, 120)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def setText(self, texto):
        self._mensagem = texto
        self._imagem = QPixmap()
        self._fps = None
        self._face_box = None
        self.update()

    def setPixmap(self, imagem):
        self._imagem = imagem
        self._mensagem = ""
        self.update()

    def clear(self):
        self.setText("")

    def set_fps(self, fps):
        self._fps = fps

    def set_face_box(self, box):
        self._face_box = box

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor("#050a10"))
        if not self._imagem.isNull():
            size = self._imagem.size().scaled(self.size(), Qt.KeepAspectRatio)
            left = (self.width() - size.width()) // 2
            top = (self.height() - size.height()) // 2
            painter.drawPixmap(left, top, size.width(), size.height(), self._imagem)
        else:
            painter.setPen(QColor("#93a9c0"))
            font = painter.font(); font.setPixelSize(17); painter.setFont(font)
            painter.drawText(self.rect().adjusted(24, 12, -24, -12),
                             Qt.AlignCenter | Qt.TextWordWrap, self._mensagem)

        # Marca de enquadramento discreta, sem recortar ou deformar o vídeo.
        if not self._imagem.isNull():
            h = self.height() * 0.72
            w = min(h * 0.78, self.width() * 0.45)
            x, y = (self.width() - w) / 2, (self.height() - h) / 2
            if self._face_box is not None:
                bx, by, bw, bh = self._face_box
                sx, sy = size.width() / self._imagem.width(), size.height() / self._imagem.height()
                x, y, w, h = left + bx*sx, top + by*sy, bw*sx, bh*sy
            painter.setPen(QPen(QColor(224, 239, 255, 170), 2))
            length = min(26, w * 0.15)
            for cx, cy, dx, dy in ((x, y, 1, 1), (x+w, y, -1, 1),
                                   (x, y+h, 1, -1), (x+w, y+h, -1, -1)):
                painter.drawLine(int(cx), int(cy), int(cx+dx*length), int(cy))
                painter.drawLine(int(cx), int(cy), int(cx), int(cy+dy*length))
            text = "CÂMERA AO VIVO"
            if self._fps is not None:
                text += f"  ·  {self._fps:.0f} FPS"
            painter.fillRect(QRectF(14, 14, 234, 28), QColor(11, 17, 24, 215))
            painter.setPen(QColor("#d7e7f7"))
            font = painter.font(); font.setPixelSize(11); painter.setFont(font)
            painter.drawText(QRectF(24, 14, 215, 28), Qt.AlignVCenter, text)


class CameraStatus(QLabel):
    """Feedback textual e de cor; nunca depende apenas da cor."""
    def __init__(self, texto="Aguardando câmera…", parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setWordWrap(True)
        self.setMinimumHeight(44)
        self.setText(texto)

    def setText(self, texto):
        super().setText(texto)
        self.setAccessibleName(texto)
        if "ERRO" in texto.upper():
            cor, fundo = "#ffaaa7", "#351d24"
        elif "LIBERADO" in texto:
            cor, fundo = "#73edb5", "#102e25"
        elif any(termo in texto.upper() for termo in ("ERRO", "BLOQUEADO", "SEM AUTORIZAÇÃO", "INDISPONÍVEL", "FALHA")):
            cor, fundo = "#ffaaa7", "#351d24"
        elif any(termo in texto.upper() for termo in ("CONFIRMANDO", "ACIONANDO")):
            cor, fundo = "#ffda87", "#30291b"
        else:
            cor, fundo = "#c4dfff", "#14283e"
        self.setStyleSheet(f"color: {cor}; background: {fundo}; border-radius: 10px; "
                          "padding: 10px 14px; font-size: 19px; font-weight: 600;")
