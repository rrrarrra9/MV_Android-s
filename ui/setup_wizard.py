"""First-run wizard: downloads SDK and scrcpy."""
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QLabel, QProgressBar,
    QTextEdit, QPushButton, QHBoxLayout
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from core.setup import SetupWorker, sdk_ready, scrcpy_ready


class SetupWizard(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configuración inicial")
        self.setMinimumSize(560, 420)
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowType.WindowContextHelpButtonHint)
        self._worker = None
        self._build()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(24, 24, 24, 24)

        title = QLabel("Configuración inicial")
        title.setFont(QFont("Segoe UI", 16, QFont.Weight.Bold))
        layout.addWidget(title)

        desc = QLabel(
            "Se descargarán automáticamente:\n"
            "  • JDK 17 portable (si no tienes Java)  (~180 MB)\n"
            "  • Android SDK cmdline-tools  (~130 MB)\n"
            "  • Android platform-tools + emulador  (~150 MB)\n"
            "  • scrcpy (visualización incrustada)  (~30 MB)\n\n"
            "Las imágenes del sistema se descargan al crear una VM."
        )
        desc.setStyleSheet("color: #aaa; font-size: 12px;")
        layout.addWidget(desc)

        self.stage_label = QLabel("Listo para instalar.")
        self.stage_label.setStyleSheet("color: #3ddc84; font-size: 12px; font-weight: bold;")
        layout.addWidget(self.stage_label)

        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        layout.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 9))
        layout.addWidget(self.log)

        btns = QHBoxLayout()
        self.skip_btn = QPushButton("Omitir (ya tengo SDK)")
        self.skip_btn.clicked.connect(self.accept)
        self.install_btn = QPushButton("Instalar todo")
        self.install_btn.setObjectName("accent")
        self.install_btn.setDefault(True)
        self.install_btn.clicked.connect(self._start)
        btns.addWidget(self.skip_btn)
        btns.addStretch()
        btns.addWidget(self.install_btn)
        layout.addLayout(btns)

    def _start(self):
        self.install_btn.setEnabled(False)
        self.skip_btn.setEnabled(False)
        self.progress.setRange(0, 0)

        self._worker = SetupWorker()
        self._worker.log.connect(self._on_log)
        self._worker.progress.connect(self._on_progress)
        self._worker.stage.connect(self.stage_label.setText)
        self._worker.finished.connect(self._on_done)
        self._worker.start()

    def _on_log(self, text):
        self.log.append(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _on_progress(self, pct):
        if self.progress.maximum() == 0:
            self.progress.setRange(0, 100)
        self.progress.setValue(pct)

    def _on_done(self, ok, err):
        self.progress.setRange(0, 100)
        self.progress.setValue(100 if ok else self.progress.value())
        if ok:
            self.stage_label.setText("Instalación completada.")
            self.stage_label.setStyleSheet("color: #3ddc84; font-weight: bold;")
            self.install_btn.setText("Continuar")
            self.install_btn.setEnabled(True)
            self.install_btn.clicked.disconnect()
            self.install_btn.clicked.connect(self.accept)
        else:
            self.stage_label.setText(f"Error: {err}")
            self.stage_label.setStyleSheet("color: #f44336; font-weight: bold;")
            self.install_btn.setText("Reintentar")
            self.install_btn.setEnabled(True)
            self.skip_btn.setEnabled(True)
