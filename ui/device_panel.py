"""
Left panel: list of AVDs with start/stop/delete controls.
"""
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QFrame, QMessageBox, QSizePolicy,
    QDialog, QFormLayout, QSpinBox
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont
from core import avd as avd_mod
from core.paths import EMULATOR
from ui.create_avd_dialog import CreateAvdDialog


class RamDialog(QDialog):
    def __init__(self, name, current_mb, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"RAM — {name}")
        self.setFixedWidth(300)
        layout = QVBoxLayout(self)
        layout.setSpacing(10)
        layout.setContentsMargins(16, 16, 16, 16)

        form = QFormLayout()
        self.spin = QSpinBox()
        self.spin.setRange(512, 16384)
        self.spin.setSingleStep(512)
        self.spin.setValue(current_mb or 2048)
        self.spin.setSuffix(" MB")
        form.addRow("RAM:", self.spin)
        layout.addLayout(form)

        presets = QHBoxLayout()
        for gb in (1, 2, 4, 6, 8):
            btn = QPushButton(f"{gb}G")
            btn.setFixedHeight(24)
            btn.setStyleSheet("font-size: 10px; padding: 0 4px;")
            btn.clicked.connect(lambda _, v=gb * 1024: self.spin.setValue(v))
            presets.addWidget(btn)
        layout.addLayout(presets)

        btns = QHBoxLayout()
        cancel = QPushButton("Cancelar")
        cancel.clicked.connect(self.reject)
        ok = QPushButton("Aplicar")
        ok.setObjectName("accent")
        ok.setDefault(True)
        ok.clicked.connect(self.accept)
        btns.addWidget(cancel)
        btns.addStretch()
        btns.addWidget(ok)
        layout.addLayout(btns)

    def value(self):
        return self.spin.value()


class AVDCard(QFrame):
    start_clicked = pyqtSignal(str)
    stop_clicked = pyqtSignal(str)
    delete_clicked = pyqtSignal(str)
    select_clicked = pyqtSignal(str)
    ram_changed = pyqtSignal(str)

    def __init__(self, info: dict, running=False, selected=False):
        super().__init__()
        self.avd_name = info["name"]
        self.setFixedHeight(72)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self._build(info)
        self.set_running(running)
        self.set_selected(selected)

    def _build(self, info):
        self.setFrameShape(QFrame.Shape.StyledPanel)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(10, 8, 10, 8)
        layout.setSpacing(8)

        left = QVBoxLayout()
        left.setSpacing(2)

        self.name_lbl = QLabel(info["name"])
        self.name_lbl.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.status_lbl = QLabel("○ Detenido")
        self.status_lbl.setStyleSheet("color: #666; font-size: 10px;")
        meta = f"{info.get('api','?')}  •  {info.get('device','?')}  •  {info.get('ram','?')}"
        self.meta_lbl = QLabel(meta)
        self.meta_lbl.setStyleSheet("color: #555; font-size: 10px;")

        left.addWidget(self.name_lbl)
        left.addWidget(self.status_lbl)
        left.addWidget(self.meta_lbl)
        layout.addLayout(left)
        layout.addStretch()

        btn_col = QVBoxLayout()
        btn_col.setSpacing(4)

        self.start_btn = QPushButton("▶")
        self.start_btn.setFixedSize(28, 28)
        self.start_btn.setToolTip("Iniciar emulador")
        self.start_btn.clicked.connect(lambda: self.start_clicked.emit(self.avd_name))

        self.stop_btn = QPushButton("■")
        self.stop_btn.setFixedSize(28, 28)
        self.stop_btn.setObjectName("danger")
        self.stop_btn.setToolTip("Detener emulador")
        self.stop_btn.clicked.connect(lambda: self.stop_clicked.emit(self.avd_name))
        self.stop_btn.hide()

        self.ram_btn = QPushButton("RAM")
        self.ram_btn.setFixedSize(36, 22)
        self.ram_btn.setStyleSheet("font-size: 9px; padding: 0;")
        self.ram_btn.setToolTip("Cambiar RAM")
        self.ram_btn.clicked.connect(self._edit_ram)

        self.del_btn = QPushButton("🗑")
        self.del_btn.setFixedSize(28, 28)
        self.del_btn.setToolTip("Eliminar VM")
        self.del_btn.clicked.connect(lambda: self.delete_clicked.emit(self.avd_name))

        btn_col.addWidget(self.start_btn)
        btn_col.addWidget(self.stop_btn)
        btn_col.addWidget(self.ram_btn)
        btn_col.addWidget(self.del_btn)
        layout.addLayout(btn_col)

    def mousePressEvent(self, event):
        self.select_clicked.emit(self.avd_name)
        super().mousePressEvent(event)

    def _edit_ram(self):
        current = avd_mod.get_avd_ram(self.avd_name) or 2048
        dlg = RamDialog(self.avd_name, current, self)
        if dlg.exec():
            new_ram = dlg.value()
            avd_mod.set_avd_ram(self.avd_name, new_ram)
            info = avd_mod.get_avd_info(self.avd_name)
            self.meta_lbl.setText(
                f"{info.get('api','?')}  •  {info.get('device','?')}  •  {info.get('ram','?')}"
            )
            self.ram_changed.emit(self.avd_name)

    def set_running(self, running: bool):
        if running:
            self.status_lbl.setText("● En ejecución")
            self.status_lbl.setStyleSheet("color: #3ddc84; font-size: 10px; font-weight: bold;")
            self.start_btn.hide()
            self.stop_btn.show()
            self.del_btn.setEnabled(False)
            self.ram_btn.setEnabled(False)
        else:
            self.status_lbl.setText("○ Detenido")
            self.status_lbl.setStyleSheet("color: #666; font-size: 10px;")
            self.start_btn.show()
            self.stop_btn.hide()
            self.del_btn.setEnabled(True)
            self.ram_btn.setEnabled(True)

    def set_selected(self, selected: bool):
        if selected:
            self.setStyleSheet("AVDCard { border: 1px solid #0078D4; border-radius: 6px; background: #1a2a3a; }")
        else:
            self.setStyleSheet("AVDCard { border: 1px solid #3a3a3a; border-radius: 6px; background: #1e1e1e; }")
            self.setStyleSheet("AVDCard { border: 1px solid #333; border-radius: 6px; background: #1e1e1e; }")

    def set_loading(self):
        self.start_btn.setEnabled(False)
        self.start_btn.setText("…")
        self.status_lbl.setText("⟳ Iniciando...")
        self.status_lbl.setStyleSheet("color: #FFC107; font-size: 10px;")


class DevicePanel(QWidget):
    avd_start = pyqtSignal(str)
    avd_stop = pyqtSignal(str)
    avd_selected = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedWidth(270)
        self._cards: dict[str, AVDCard] = {}
        self._selected = None
        self._build()
        self._refresh()

        self._timer = QTimer(self)
        self._timer.timeout.connect(self._refresh)
        self._timer.start(20000)

    def _build(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QFrame()
        header.setFixedHeight(48)
        header.setStyleSheet("background: #242424; border-bottom: 1px solid #333;")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 0, 8, 0)

        title = QLabel("Máquinas virtuales")
        title.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        hl.addWidget(title)
        hl.addStretch()

        self.add_btn = QPushButton("+")
        self.add_btn.setFixedSize(28, 28)
        self.add_btn.setObjectName("accent")
        self.add_btn.setToolTip("Nueva VM")
        self.add_btn.clicked.connect(self._open_create)
        hl.addWidget(self.add_btn)
        layout.addWidget(header)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: #1a1a1a; border: none;")
        self._container = QWidget()
        self._container.setStyleSheet("background: #1a1a1a;")
        self._vbox = QVBoxLayout(self._container)
        self._vbox.setContentsMargins(8, 8, 8, 8)
        self._vbox.setSpacing(6)
        self._vbox.setAlignment(Qt.AlignmentFlag.AlignTop)
        scroll.setWidget(self._container)
        layout.addWidget(scroll)

        self._empty_lbl = QLabel("Sin VMs.\nHaz clic en + para crear una.")
        self._empty_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._empty_lbl.setStyleSheet("color: #444; font-size: 11px;")
        self._empty_lbl.hide()
        layout.addWidget(self._empty_lbl)

        if not EMULATOR.exists():
            self.add_btn.setEnabled(False)
            self.add_btn.setToolTip("Instala el SDK primero")

    def _refresh(self):
        avds = avd_mod.list_avds()
        running = set(avd_mod.get_running_emulators().keys())

        existing = set(self._cards.keys())
        new_set = set(avds)

        for name in existing - new_set:
            card = self._cards.pop(name)
            self._vbox.removeWidget(card)
            card.deleteLater()

        for name in new_set - existing:
            info = avd_mod.get_avd_info(name)
            card = AVDCard(info, running=name in running, selected=name == self._selected)
            card.start_clicked.connect(self._on_start)
            card.stop_clicked.connect(self._on_stop)
            card.delete_clicked.connect(self._on_delete)
            card.select_clicked.connect(self._on_select)
            self._cards[name] = card
            self._vbox.addWidget(card)

        for name, card in self._cards.items():
            card.set_running(name in running)
            card.set_selected(name == self._selected)

        self._empty_lbl.setVisible(len(avds) == 0)

    def mark_loading(self, name):
        if name in self._cards:
            self._cards[name].set_loading()

    def mark_running(self, name):
        if name in self._cards:
            self._cards[name].set_running(True)

    def mark_stopped(self, name):
        if name in self._cards:
            self._cards[name].set_running(False)

    def _on_start(self, name):
        self.mark_loading(name)
        self.avd_start.emit(name)

    def _on_stop(self, name):
        self.avd_stop.emit(name)

    def _on_select(self, name):
        self._selected = name
        self.avd_selected.emit(name)
        self._refresh()

    def _on_delete(self, name):
        reply = QMessageBox.question(
            self, "Eliminar VM",
            f"¿Eliminar '{name}' y todos sus datos?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            avd_mod.delete_avd(name)
            self._refresh()

    def _open_create(self):
        dlg = CreateAvdDialog(self)
        if dlg.exec():
            self._refresh()
