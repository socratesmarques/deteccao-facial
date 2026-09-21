from datetime import datetime

from PySide6.QtCore import QDate
from PySide6.QtWidgets import (
    QAbstractItemView, QCheckBox, QComboBox, QDateEdit, QHeaderView,
    QHBoxLayout, QLabel, QLineEdit, QPushButton, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)
from access_logger import AccessLogger


class PaginaLogs(QWidget):
    def __init__(self, pode_administrar=lambda: False):
        super().__init__()
        self.pode_administrar = pode_administrar
        self.logger = AccessLogger()
        layout = QVBoxLayout(self)
        title = QLabel('Histórico de acessos')
        title.setStyleSheet('font-size: 26px; font-weight: 700;')
        layout.addWidget(title)
        info = QLabel('Entradas e saídas registradas no reconhecimento. O sentido é escolhido na tela da câmera.')
        info.setWordWrap(True)
        layout.addWidget(info)
        filters = QHBoxLayout()
        self.pessoa = QLineEdit(); self.pessoa.setPlaceholderText('Pesquisar pessoa')
        self.movimento = QComboBox()
        for text, value in [('Todos os sentidos', ''), ('Entrada', 'ENTRADA'), ('Saída', 'SAIDA')]:
            self.movimento.addItem(text, value)
        self.decisao = QComboBox()
        for text, value in [('Todos os resultados', ''), ('Liberado', 'LIBERADO'), ('Bloqueado', 'BLOQUEADO'), ('Erro', 'ERRO')]:
            self.decisao.addItem(text, value)
        for widget in (self.pessoa, self.movimento, self.decisao):
            filters.addWidget(widget)
        layout.addLayout(filters)
        dates = QHBoxLayout()
        self.filtrar_data = QCheckBox('Filtrar dia')
        self.data = QDateEdit(QDate.currentDate()); self.data.setCalendarPopup(True)
        self.data.setDisplayFormat('dd/MM/yyyy'); self.data.setEnabled(False)
        self.filtrar_data.toggled.connect(self.data.setEnabled)
        atualizar = QPushButton('Atualizar')
        atualizar.clicked.connect(self.atualizar)
        dates.addWidget(self.filtrar_data); dates.addWidget(self.data)
        dates.addStretch(); dates.addWidget(atualizar)
        layout.addLayout(dates)
        self.total = QLabel(); layout.addWidget(self.total)
        self.tabela = QTableWidget(0, 5)
        self.tabela.setHorizontalHeaderLabels(['Data e hora', 'Pessoa', 'Movimento', 'Resultado', 'Detalhe'])
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.verticalHeader().hide()
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabela.setMinimumHeight(180)
        layout.addWidget(self.tabela, 1)
        self.pessoa.returnPressed.connect(self.atualizar)
        self.movimento.currentIndexChanged.connect(self.atualizar)
        self.decisao.currentIndexChanged.connect(self.atualizar)
        self.filtrar_data.toggled.connect(self.atualizar)
        self.data.dateChanged.connect(self.atualizar)
        self.atualizar()

    def atualizar(self, *_):
        self.tabela.setRowCount(0)
        if not self.pode_administrar():
            self.total.setText('Sessão bloqueada.')
            return
        try:
            rows = self.logger.listar(
                pessoa=self.pessoa.text().strip(), movimento=self.movimento.currentData(),
                decisao=self.decisao.currentData(),
                data=self.data.date().toString('yyyy-MM-dd') if self.filtrar_data.isChecked() else '',
            )
        except (OSError, ValueError) as error:
            self.total.setText(f'Não foi possível abrir os logs: {error}')
            return
        if not self.pode_administrar():
            self.total.setText('Sessão bloqueada.')
            return
        self.tabela.setRowCount(len(rows))
        for i, row in enumerate(rows):
            try:
                timestamp = datetime.fromisoformat(row['data_hora']).strftime('%d/%m/%Y %H:%M:%S %z')
            except ValueError:
                timestamp = row['data_hora']
            movement = {'ENTRADA': 'Entrada', 'SAIDA': 'Saída'}.get(row['movimento'], 'Não informado')
            values = [timestamp, row['pessoa'].title(), movement, row['decisao'], row['detalhe']]
            for j, value in enumerate(values):
                self.tabela.setItem(i, j, QTableWidgetItem(value))
        self.total.setText(f'{len(rows)} registro(s) · até 500 mais recentes por filtro' if rows else 'Nenhum registro encontrado.')
