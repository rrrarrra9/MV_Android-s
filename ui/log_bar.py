"""Collapsible log bar at the bottom."""
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTextEdit
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class LogBar(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumHeight(200)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget()
        header.setFixedHeight(28)
        header.setStyleSheet("background: #242424; border-top: 1px solid #333;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 0, 8, 0)

        lbl = QLabel("Logs")
        lbl.setStyleSheet("color: #888; font-size: 11px;")
        hl.addWidget(lbl)
        hl.addStretch()

        self._clear_btn = QPushButton("Limpiar")
        self._clear_btn.setFixedHeight(20)
        self._clear_btn.setStyleSheet("font-size: 10px; padding: 0 6px;")
        self._clear_btn.clicked.connect(self.clear)
        hl.addWidget(self._clear_btn)

        layout.addWidget(header)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setFont(QFont("Consolas", 9))
        self._log.setStyleSheet("background: #0d0d0d; color: #999; border: none;")
        layout.addWidget(self._log)

    _MAX_LINES = 500

    def append(self, text):
        doc = self._log.document()
        if doc.blockCount() > self._MAX_LINES:
            cursor = self._log.textCursor()
            cursor.movePosition(cursor.MoveOperation.Start)
            cursor.select(cursor.SelectionType.LineUnderCursor)
            cursor.removeSelectedText()
            cursor.deleteChar()
        self._log.append(text)
        self._log.verticalScrollBar().setValue(self._log.verticalScrollBar().maximum())

    def clear(self):
        self._log.clear()
