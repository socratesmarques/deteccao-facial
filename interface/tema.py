"""Tema compartilhado da interface para uso em display e computador."""

TEMA = """
QWidget { background: #0b1118; color: #e8eef5; font-family: 'DejaVu Sans'; font-size: 14px; }
QMainWindow, QStackedWidget { background: #0b1118; }
QFrame#cabecalho { background: #101a25; border-bottom: 1px solid #243343; }
QLabel { background: transparent; }
QLabel#marca { color: #ffffff; font-size: 20px; font-weight: 700; }
QLabel#subtitulo, QLabel#rodape { color: #92a5b9; font-size: 12px; }
QLabel#secao { color: #92a5b9; font-size: 12px; font-weight: 600; }
QPushButton { background: #1c2b3b; border: 1px solid #33475b; border-radius: 9px;
              padding: 10px 16px; min-height: 24px; font-weight: 600; }
QPushButton:hover { background: #283d52; border-color: #63819e; }
QPushButton:pressed { background: #334d66; }
QPushButton:disabled { color: #64758a; border-color: #233244; background: #14202d; }
QPushButton#primario { background: #236bda; border-color: #3c82ed; color: white; }
QPushButton#primario:hover { background: #307bed; }
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox { background: #142130; border: 1px solid #3a5067;
    border-radius: 7px; padding: 9px; min-height: 24px; selection-background-color: #236bda; }
QComboBox QAbstractItemView { background: #142130; selection-background-color: #236bda; }
QGroupBox { border: 1px solid #293e52; border-radius: 10px; margin-top: 20px; padding: 18px 12px 12px; }
QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 0 5px; color: #a9bfd5; }
QCheckBox { spacing: 10px; min-height: 36px; }
QCheckBox::indicator { width: 24px; height: 24px; }
QProgressBar { background: #162333; border: none; border-radius: 7px; min-height: 16px; text-align: center; }
QProgressBar::chunk { background: #448aff; border-radius: 7px; }
QScrollArea { border: none; }
QScrollBar:vertical { background: #101a25; width: 12px; border-radius: 6px; }
QScrollBar::handle:vertical { background: #3a526a; min-height: 32px; border-radius: 6px; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QMenu { background: #142130; border: 1px solid #3a5067; padding: 6px; }
QMenu::item { padding: 14px 24px; border-radius: 5px; }
QMenu::item:selected { background: #284360; }
QMenu::separator { height: 1px; background: #33475b; margin: 5px; }
"""
