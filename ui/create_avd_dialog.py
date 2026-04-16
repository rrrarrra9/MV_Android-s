from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox,
    QSpinBox, QPushButton, QHBoxLayout, QTextEdit, QProgressBar,
    QLabel, QMessageBox
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from core import avd as avd_mod
from core.paths import SDK_DIR
from core.setup import SetupWorker


SYSTEM_IMAGES = [
    ("system-images;android-35;google_apis_playstore;x86_64", "Android 15 (API 35) — Play Store"),
    ("system-images;android-34;google_apis_playstore;x86_64", "Android 14 (API 34) — Play Store"),
    ("system-images;android-33;google_apis_playstore;x86_64", "Android 13 (API 33) — Play Store"),
    ("system-images;android-32;google_apis;x86_64",           "Android 12L (API 32)"),
    ("system-images;android-31;google_apis;x86_64",           "Android 12 (API 31)"),
    ("system-images;android-30;google_apis_playstore;x86_64", "Android 11 (API 30) — Play Store"),
]

DEVICES = [
    ("pixel_8",       "Pixel 8"),
    ("pixel_8_pro",   "Pixel 8 Pro"),
    ("pixel_7",       "Pixel 7"),
    ("pixel_6",       "Pixel 6"),
    ("pixel_5",       "Pixel 5"),
    ("pixel_4",       "Pixel 4"),
    ("medium_phone",  "Medium Phone"),
    ("Nexus 5X",      "Nexus 5X"),
    ("Nexus 6",       "Nexus 6"),
]


class CreateAvdDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Nueva máquina virtual Android")
        self.setMinimumWidth(480)
        self._worker = None
        self._build()
        self._refresh_installed_images()

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(20, 20, 20, 20)

        form = QFormLayout()
        form.setSpacing(8)

        self.name_edit = QLineEdit("MiAndroid")
        form.addRow("Nombre:", self.name_edit)

        self.device_combo = QComboBox()
        for val, label in DEVICES:
            self.device_combo.addItem(label, val)
        form.addRow("Dispositivo:", self.device_combo)

        self.image_combo = QComboBox()
        form.addRow("Sistema:", self.image_combo)

        ram_widget = QWidget()
        ram_layout = QHBoxLayout(ram_widget)
        ram_layout.setContentsMargins(0, 0, 0, 0)
        ram_layout.setSpacing(4)

        self.ram_spin = QSpinBox()
        self.ram_spin.setRange(512, 16384)
        self.ram_spin.setSingleStep(512)
        self.ram_spin.setValue(2048)
        self.ram_spin.setSuffix(" MB")
        ram_layout.addWidget(self.ram_spin)

        for gb in (1, 2, 4, 6, 8):
            btn = QPushButton(f"{gb}G")
            btn.setFixedWidth(32)
            btn.setFixedHeight(24)
            btn.setStyleSheet("font-size: 10px; padding: 0;")
            btn.clicked.connect(lambda _, v=gb * 1024: self.ram_spin.setValue(v))
            ram_layout.addWidget(btn)

        form.addRow("RAM:", ram_widget)

        self.storage_spin = QSpinBox()
        self.storage_spin.setRange(2048, 32768)
        self.storage_spin.setSingleStep(1024)
        self.storage_spin.setValue(8192)
        self.storage_spin.setSuffix(" MB")
        form.addRow("Almacenamiento:", self.storage_spin)

        layout.addLayout(form)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setFont(QFont("Consolas", 9))
        self.log.setMaximumHeight(130)
        self.log.hide()
        layout.addWidget(self.log)

        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.hide()
        layout.addWidget(self.progress)

        btns = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        self.create_btn = QPushButton("Crear VM")
        self.create_btn.setObjectName("accent")
        self.create_btn.setDefault(True)
        self.create_btn.clicked.connect(self._start_create)
        btns.addWidget(cancel)
        btns.addStretch()
        btns.addWidget(self.create_btn)
        layout.addLayout(btns)

    def _refresh_installed_images(self):
        installed = set(avd_mod.list_installed_images())
        self.image_combo.clear()
        for pkg, label in SYSTEM_IMAGES:
            suffix = " ✓" if pkg in installed else " (se descargará)"
            self.image_combo.addItem(label + suffix, pkg)

    def _start_create(self):
        name = self.name_edit.text().strip().replace(" ", "_")
        if not name:
            QMessageBox.warning(self, "Error", "El nombre no puede estar vacío.")
            return

        pkg = self.image_combo.currentData()
        device = self.device_combo.currentData()
        ram = self.ram_spin.value()
        storage = self.storage_spin.value()

        self.create_btn.setEnabled(False)
        self.log.show()
        self.progress.show()

        self._worker = avd_mod.create_avd(
            name, pkg, device, ram, storage,
            log_cb=self._on_log,
            finished_cb=self._on_done,
        )

    def _on_log(self, text):
        self.log.append(text)
        self.log.verticalScrollBar().setValue(self.log.verticalScrollBar().maximum())

    def _on_done(self, ok, err):
        self.progress.hide()
        if ok:
            self.log.append("\n✓ VM creada correctamente.")
            self.create_btn.setText("Cerrar")
            self.create_btn.setEnabled(True)
            self.create_btn.clicked.disconnect()
            self.create_btn.clicked.connect(self.accept)
        else:
            self.log.append(f"\n✗ Error:\n{err}")
            self.create_btn.setText("Reintentar")
            self.create_btn.setEnabled(True)
