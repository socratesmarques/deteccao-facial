from PySide6.QtWidgets import QDialog, QDialogButtonBox, QLabel, QLineEdit, QVBoxLayout


class AdminDialog(QDialog):
    def __init__(self, auth, parent=None, alterar=False):
        super().__init__(parent)
        self.auth = auth
        self.alterar = alterar
        self.primeiro = not auth.configurado()
        self.setWindowTitle('Administração · FaceAI')
        self.setMinimumWidth(390)
        self.setMaximumWidth(550)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 24, 24, 24)
        titulo = 'Defina a senha do administrador' if self.primeiro else 'Acesso administrativo'
        if alterar:
            titulo = 'Alterar senha administrativa'
        label = QLabel(titulo)
        label.setStyleSheet('font-size: 20px; font-weight: 700;')
        label.setWordWrap(True)
        layout.addWidget(label)
        info = QLabel('Esta senha protege cadastros, autorizações e configurações.' if self.primeiro
                      else 'Digite sua senha para continuar.')
        info.setWordWrap(True)
        layout.addWidget(info)
        self.atual = None
        if alterar:
            self.atual = QLineEdit()
            self.atual.setEchoMode(QLineEdit.Password)
            self.atual.setPlaceholderText('Senha atual')
            self.atual.setMaxLength(256)
            layout.addWidget(self.atual)
        self.senha = QLineEdit()
        self.senha.setEchoMode(QLineEdit.Password)
        self.senha.setMaxLength(256)
        self.senha.setPlaceholderText('Nova senha · mínimo de 8 caracteres' if self.primeiro or alterar else 'Senha')
        layout.addWidget(self.senha)
        self.confirmacao = None
        if self.primeiro or alterar:
            self.confirmacao = QLineEdit()
            self.confirmacao.setEchoMode(QLineEdit.Password)
            self.confirmacao.setMaxLength(256)
            self.confirmacao.setPlaceholderText('Repita a nova senha')
            layout.addWidget(self.confirmacao)
        self.erro = QLabel()
        self.erro.setWordWrap(True)
        self.erro.setStyleSheet('color: #ffaaa7;')
        layout.addWidget(self.erro)
        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.button(QDialogButtonBox.Ok).setText('Salvar senha' if self.primeiro or alterar else 'Entrar')
        botoes.button(QDialogButtonBox.Cancel).setText('Cancelar')
        botoes.accepted.connect(self.validar)
        botoes.rejected.connect(self.reject)
        layout.addWidget(botoes)

    def validar(self):
        password = self.senha.text()
        try:
            if self.confirmacao is not None and password != self.confirmacao.text():
                raise ValueError('As senhas não coincidem.')
            if self.alterar:
                self.auth.alterar(self.atual.text(), password)
            elif self.primeiro:
                self.auth.criar(password)
            elif not self.auth.verificar(password):
                raise ValueError('Senha incorreta.')
        except (ValueError, RuntimeError, OSError) as error:
            self.erro.setText(str(error))
            self.senha.clear()
            self.senha.setFocus()
            return
        self.senha.clear()
        if self.atual is not None:
            self.atual.clear()
        if self.confirmacao is not None:
            self.confirmacao.clear()
        self.accept()

    def done(self, result):
        for field in (self.senha, self.atual, self.confirmacao):
            if field is not None:
                field.clear()
        super().done(result)
