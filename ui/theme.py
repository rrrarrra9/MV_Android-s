from PyQt6.QtGui import QPalette, QColor, QFont
from PyQt6.QtWidgets import QApplication

BG = "#1a1a1a"
BG2 = "#242424"
BG3 = "#2d2d2d"
BORDER = "#3a3a3a"
ACCENT = "#3ddc84"       # Android green
ACCENT2 = "#0078D4"      # blue for actions
TEXT = "#e8e8e8"
TEXT_DIM = "#888"
RED = "#f44336"
YELLOW = "#FFC107"


def apply_dark(app: QApplication):
    app.setStyle("Fusion")
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window,          QColor(BG))
    pal.setColor(QPalette.ColorRole.WindowText,      QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Base,            QColor(BG2))
    pal.setColor(QPalette.ColorRole.AlternateBase,   QColor(BG3))
    pal.setColor(QPalette.ColorRole.ToolTipBase,     QColor(BG3))
    pal.setColor(QPalette.ColorRole.ToolTipText,     QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Text,            QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Button,          QColor(BG3))
    pal.setColor(QPalette.ColorRole.ButtonText,      QColor(TEXT))
    pal.setColor(QPalette.ColorRole.Highlight,       QColor(ACCENT2))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor("#fff"))
    app.setPalette(pal)


STYLESHEET = f"""
QMainWindow, QDialog, QWidget {{
    background: {BG};
    color: {TEXT};
    font-family: 'Segoe UI', sans-serif;
    font-size: 13px;
}}
QGroupBox {{
    border: 1px solid {BORDER};
    border-radius: 6px;
    margin-top: 8px;
    padding-top: 8px;
    font-size: 11px;
    color: {TEXT_DIM};
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    left: 10px;
    padding: 0 4px;
}}
QPushButton {{
    background: {BG3};
    color: {TEXT};
    border: 1px solid {BORDER};
    border-radius: 5px;
    padding: 5px 14px;
    font-size: 12px;
}}
QPushButton:hover {{ background: #3a3a3a; }}
QPushButton:pressed {{ background: #222; }}
QPushButton:disabled {{ color: #555; border-color: #2a2a2a; }}
QPushButton#accent {{
    background: {ACCENT2};
    border-color: {ACCENT2};
    color: #fff;
    font-weight: bold;
}}
QPushButton#accent:hover {{ background: #106EBE; }}
QPushButton#green {{
    background: #2d6a3f;
    border-color: {ACCENT};
    color: {ACCENT};
    font-weight: bold;
}}
QPushButton#green:hover {{ background: #3a7d4f; }}
QPushButton#danger {{
    background: #4a1a1a;
    border-color: {RED};
    color: {RED};
}}
QPushButton#danger:hover {{ background: #5a2020; }}
QLineEdit, QComboBox, QSpinBox {{
    background: {BG2};
    border: 1px solid {BORDER};
    border-radius: 4px;
    padding: 4px 8px;
    color: {TEXT};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus {{
    border-color: {ACCENT2};
}}
QComboBox::drop-down {{ border: none; }}
QComboBox QAbstractItemView {{
    background: {BG2};
    selection-background-color: {ACCENT2};
}}
QTextEdit {{
    background: #0f0f0f;
    color: #b0b0b0;
    border: 1px solid {BORDER};
    border-radius: 4px;
    font-family: 'Consolas', monospace;
    font-size: 11px;
}}
QTabWidget::pane {{
    border: 1px solid {BORDER};
    border-radius: 4px;
}}
QTabBar::tab {{
    background: {BG2};
    color: {TEXT_DIM};
    padding: 5px 14px;
    border: 1px solid {BORDER};
    border-bottom: none;
    border-top-left-radius: 4px;
    border-top-right-radius: 4px;
}}
QTabBar::tab:selected {{
    background: {BG3};
    color: {TEXT};
    border-bottom: 2px solid {ACCENT};
}}
QScrollArea {{ border: none; }}
QScrollBar:vertical {{
    background: {BG};
    width: 8px;
    border-radius: 4px;
}}
QScrollBar::handle:vertical {{
    background: {BORDER};
    border-radius: 4px;
}}
QProgressBar {{
    background: {BG2};
    border: 1px solid {BORDER};
    border-radius: 4px;
    height: 8px;
    text-align: center;
}}
QProgressBar::chunk {{
    background: {ACCENT2};
    border-radius: 4px;
}}
QSplitter::handle {{ background: {BORDER}; }}
QCheckBox::indicator {{
    width: 14px;
    height: 14px;
    border: 1px solid {BORDER};
    border-radius: 3px;
    background: {BG2};
}}
QCheckBox::indicator:checked {{
    background: {ACCENT2};
    border-color: {ACCENT2};
}}
"""
