import subprocess
import shutil
from pathlib import Path
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QSplitter, QFrame, QLabel, QPushButton, QLineEdit,
    QMessageBox, QStatusBar
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

from core.emulator import EmulatorLaunchThread
from core.paths import ADB, SDK_DIR, SCRCPY_EXE
from core import avd as avd_mod
from ui.device_panel import DevicePanel
from ui.screen_view import ScreenView
from ui.log_bar import LogBar
from ui.theme import STYLESHEET


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Android Emulator Manager — Expo / React Native")
        self.setMinimumSize(1000, 660)
        self.resize(1280, 760)
        self.setStyleSheet(STYLESHEET)

        self._emulator_threads: dict[str, EmulatorLaunchThread] = {}
        self._selected_avd = None

        self._build()

    def _build(self):
        root = QWidget()
        self.setCentralWidget(root)
        vbox = QVBoxLayout(root)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(0)

        vbox.addWidget(self._build_toolbar())

        content = QSplitter(Qt.Orientation.Horizontal)
        content.setHandleWidth(1)

        self._device_panel = DevicePanel()
        self._device_panel.avd_start.connect(self._launch_avd)
        self._device_panel.avd_stop.connect(self._stop_avd)
        self._device_panel.avd_selected.connect(self._on_avd_selected)
        content.addWidget(self._device_panel)

        right = QWidget()
        right_v = QVBoxLayout(right)
        right_v.setContentsMargins(0, 0, 0, 0)
        right_v.setSpacing(0)

        self._screen = ScreenView()
        self._screen.log.connect(self._log)
        right_v.addWidget(self._screen, 1)

        self._logbar = LogBar()
        right_v.addWidget(self._logbar)

        content.addWidget(right)
        content.setSizes([270, 1010])
        content.setStretchFactor(0, 0)
        content.setStretchFactor(1, 1)

        vbox.addWidget(content, 1)

        self.status = QStatusBar()
        self.setStatusBar(self.status)
        self.status.showMessage("Listo")

    def _build_toolbar(self):
        bar = QFrame()
        bar.setFixedHeight(50)
        bar.setStyleSheet("background: #1e1e1e; border-bottom: 1px solid #2e2e2e;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(16, 0, 16, 0)

        logo = QLabel("📱 Android Emulator Manager")
        logo.setFont(QFont("Segoe UI", 13, QFont.Weight.Bold))
        logo.setStyleSheet("color: #3ddc84;")
        layout.addWidget(logo)
        layout.addStretch()

        self._adb_input = QLineEdit()
        self._adb_input.setPlaceholderText("adb command (ej: shell getprop ro.build.version.release)")
        self._adb_input.setFixedWidth(340)
        self._adb_input.returnPressed.connect(self._run_adb)
        layout.addWidget(self._adb_input)

        run_adb = QPushButton("ADB ▶")
        run_adb.setFixedWidth(70)
        run_adb.clicked.connect(self._run_adb)
        layout.addWidget(run_adb)

        return bar

    def _log(self, msg):
        self._logbar.append(msg)
        self.status.showMessage(msg[:80], 4000)

    def _on_avd_selected(self, name):
        self._selected_avd = name

    def _launch_avd(self, name):
        if name in self._emulator_threads:
            self._log(f"{name} ya está iniciándose.")
            return
        if not SCRCPY_EXE.exists():
            QMessageBox.critical(self, "scrcpy no encontrado",
                "scrcpy no está instalado. Ejecuta la configuración inicial.")
            return

        self._screen.show_booting(name)
        self._log(f"Lanzando {name}...")

        thread = EmulatorLaunchThread(name)
        thread.log.connect(self._log)
        thread.booted.connect(self._on_booted)
        thread.stopped.connect(self._on_stopped)
        thread.error.connect(lambda e: self._log(f"Error: {e}"))
        self._emulator_threads[name] = thread
        thread.start()

        self._device_panel.mark_loading(name)

    def _on_booted(self, avd_name, serial):
        self._log(f"Emulador {avd_name} listo — serial: {serial}")
        self._device_panel.mark_running(avd_name)
        if self._selected_avd == avd_name or self._selected_avd is None:
            self._screen.attach_serial(avd_name, serial)

    def _on_stopped(self, avd_name):
        self._log(f"{avd_name} detenido.")
        self._emulator_threads.pop(avd_name, None)
        self._device_panel.mark_stopped(avd_name)
        if self._selected_avd == avd_name:
            self._screen.show_empty()

    def _stop_avd(self, name):
        thread = self._emulator_threads.get(name)
        if thread:
            thread.stop()
        else:
            running = avd_mod.get_running_emulators()
            serial = running.get(name)
            if serial and ADB.exists():
                env_copy = __import__("os").environ.copy()
                env_copy["ANDROID_HOME"] = str(SDK_DIR)
                subprocess.run([str(ADB), "-s", serial, "emu", "kill"],
                               capture_output=True, env=env_copy)

    def _run_adb(self):
        cmd = self._adb_input.text().strip()
        if not cmd:
            return
        adb = str(ADB) if ADB.exists() else shutil.which("adb") or "adb"

        running = avd_mod.get_running_emulators()
        target = ""
        if self._selected_avd and self._selected_avd in running:
            target = f"-s {running[self._selected_avd]}"

        full_cmd = f'"{adb}" {target} {cmd}'
        self._log(f"$ adb {target} {cmd}")

        import threading
        def _run():
            result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True)
            out = result.stdout + result.stderr
            for line in out.splitlines():
                self._logbar.append(line)
        threading.Thread(target=_run, daemon=True).start()
        self._adb_input.clear()

    def closeEvent(self, event):
        active = list(self._emulator_threads.values())
        if active:
            reply = QMessageBox.question(
                self, "Emuladores activos",
                f"Hay {len(active)} emulador(es) corriendo. ¿Detenerlos y salir?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
            for t in active:
                t.stop()
        self._screen.cleanup()
        event.accept()
