"""
Central area: embeds scrcpy window for a running emulator.
Shows a boot-wait overlay until the emulator is ready.
"""
import ctypes
import ctypes.wintypes
import time
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QLabel, QStackedLayout, QFrame
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSignal as Signal
from PyQt6.QtGui import QFont
from core.emulator import ScrcpyEmbedThread, embed_window, _resize_embedded
from core.paths import SCRCPY_EXE, ADB
import subprocess
import os


user32 = ctypes.windll.user32


class BootOverlay(QWidget):
    def __init__(self, avd_name, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.spinner = QLabel("⟳")
        self.spinner.setFont(QFont("Segoe UI", 48))
        self.spinner.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner.setStyleSheet("color: #3ddc84;")

        self.msg = QLabel(f"Iniciando {avd_name}...")
        self.msg.setFont(QFont("Segoe UI", 14))
        self.msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.msg.setStyleSheet("color: #888;")

        self.sub = QLabel("Esto puede tardar 1-2 minutos la primera vez.")
        self.sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.sub.setStyleSheet("color: #555; font-size: 11px;")

        layout.addWidget(self.spinner)
        layout.addWidget(self.msg)
        layout.addWidget(self.sub)

        self._anim_timer = QTimer(self)
        self._anim_timer.timeout.connect(self._spin)
        self._anim_timer.start(200)
        self._frames = ["⟳", "↻", "⟲", "↺"]
        self._fi = 0

    def _spin(self):
        self._fi = (self._fi + 1) % len(self._frames)
        self.spinner.setText(self._frames[self._fi])

    def set_message(self, msg):
        self.msg.setText(msg)


class EmptyView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        icon = QLabel("📱")
        icon.setFont(QFont("Segoe UI", 64))
        icon.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg = QLabel("Selecciona una VM e iníciala\npara ver la pantalla aquí.")
        msg.setFont(QFont("Segoe UI", 13))
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("color: #444;")
        layout.addWidget(icon)
        layout.addWidget(msg)


class BootWatcher(QThread):
    booted = Signal()
    log = Signal(str)

    def __init__(self, serial):
        super().__init__()
        self.serial = serial
        self._alive = True

    def run(self):
        from core.paths import ADB, SDK_DIR
        env = os.environ.copy()
        env["ANDROID_HOME"] = str(SDK_DIR)
        deadline = time.time() + 180
        while time.time() < deadline and self._alive:
            try:
                r = subprocess.run(
                    [str(ADB), "-s", self.serial, "shell", "getprop", "sys.boot_completed"],
                    capture_output=True, text=True, timeout=5, env=env
                )
                if r.stdout.strip() == "1":
                    self.log.emit("Sistema arrancado.")
                    self.booted.emit()
                    return
            except Exception:
                pass
            self.log.emit("Esperando arranque del sistema...")
            time.sleep(3)

    def stop(self):
        self._alive = False


class ScreenView(QWidget):
    log = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("background: #111;")
        self.setMinimumSize(300, 400)

        self._stack = QStackedLayout(self)
        self._stack.setContentsMargins(0, 0, 0, 0)

        self._empty = EmptyView()
        self._stack.addWidget(self._empty)

        # Wrapper keeps the embed container centered at phone aspect ratio
        self._embed_wrapper = QWidget()
        self._embed_wrapper.setStyleSheet("background: #000;")
        wrapper_layout = QHBoxLayout(self._embed_wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)

        self._embed_container = QWidget()
        self._embed_container.setStyleSheet("background: #000;")
        wrapper_layout.addStretch()
        wrapper_layout.addWidget(self._embed_container)
        wrapper_layout.addStretch()

        self._stack.addWidget(self._embed_wrapper)

        self._overlay = None
        self._scrcpy_thread = None
        self._current_hwnd = None
        self._current_avd = None

        self._stack.setCurrentWidget(self._empty)

        self._resize_timer = QTimer(self)
        self._resize_timer.timeout.connect(self._sync_embed_size)
        self._resize_timer.setSingleShot(True)

    def show_booting(self, avd_name):
        self._current_avd = avd_name
        self._clear_overlay()
        self._update_container_size()
        self._overlay = BootOverlay(avd_name, self._embed_wrapper)
        self._overlay.setGeometry(0, 0, self._embed_wrapper.width(), self._embed_wrapper.height())
        self._overlay.show()
        self._stack.setCurrentWidget(self._embed_wrapper)

    def attach_serial(self, avd_name, serial):
        self._current_avd = avd_name
        self._current_serial = serial
        if not serial:
            if self._overlay:
                self._overlay.set_message("Error: no se encontró serial del emulador.")
            self.log.emit("Error: serial vacío, no se puede conectar scrcpy.")
            return
        if self._overlay:
            self._overlay.set_message(f"Conectando pantalla de {avd_name}...")
        self._start_scrcpy(avd_name, serial)

    def _on_boot_log(self, msg):
        if self._overlay:
            self._overlay.set_message(msg)
        self.log.emit(msg)

    def _start_scrcpy(self, avd_name, serial):
        self.log.emit(f"Conectando scrcpy a {serial}...")
        if self._scrcpy_thread:
            self._scrcpy_thread.stop()

        self._update_container_size()
        container_size = (self._embed_container.width(), self._embed_container.height())
        self._scrcpy_thread = ScrcpyEmbedThread(serial, avd_name, container_size=container_size)
        self._scrcpy_thread.log.connect(self.log)
        self._scrcpy_thread.hwnd_ready.connect(self._on_hwnd_ready)
        self._scrcpy_thread.stopped.connect(self._on_scrcpy_stopped)
        self._scrcpy_thread.start()

        QTimer.singleShot(8000, self._poll_hwnd)

    def _poll_hwnd(self):
        if self._current_hwnd:
            return
        title = f"scrcpy_{self._current_avd}"
        buf = ctypes.create_unicode_buffer(512)
        found = []

        def _cb(hwnd, _):
            user32.GetWindowTextW(hwnd, buf, 512)
            t = buf.value
            if t:
                self.log.emit(f"[poll] hwnd={hwnd:#x} title={t!r}")
            if title.lower() in t.lower():
                found.append(hwnd)
            return True

        EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)
        user32.EnumWindows(EnumWindowsProc(_cb), 0)
        if found:
            self.log.emit(f"[poll] encontrado hwnd={found[0]:#x}")
            self._on_hwnd_ready(found[0])
        else:
            self.log.emit(f"[poll] no encontrado '{title}', reintentando...")
            QTimer.singleShot(3000, self._poll_hwnd)

    def _on_hwnd_ready(self, hwnd):
        self._current_hwnd = hwnd
        self._clear_overlay()
        self.log.emit("Pantalla del emulador conectada.")
        self._update_container_size()
        embed_window(hwnd, self._embed_container)
        self._stack.setCurrentWidget(self._embed_wrapper)
        QTimer.singleShot(300, self._sync_embed_size)
        QTimer.singleShot(1500, self._sync_embed_size)

    def _on_scrcpy_stopped(self):
        self._current_hwnd = None
        self.log.emit("scrcpy desconectado.")

    def show_empty(self):
        self._clear_scrcpy()
        self._clear_overlay()
        self._stack.setCurrentWidget(self._empty)
        self._current_avd = None
        self._current_hwnd = None

    def _update_container_size(self):
        """Resize _embed_container to vertical phone ratio within the wrapper."""
        total_h = self.height()
        total_w = self.width()
        # 9:19.5 aspect ratio (typical phone)
        container_w = int(total_h * 9 / 19.5)
        if container_w > total_w:
            container_w = total_w
        self._embed_container.setFixedSize(container_w, total_h)

    def _clear_overlay(self):
        if self._overlay:
            self._overlay.hide()
            self._overlay.deleteLater()
            self._overlay = None

    def _clear_scrcpy(self):
        if self._scrcpy_thread:
            self._scrcpy_thread.stop()
            self._scrcpy_thread = None

    def cleanup(self):
        if self._current_hwnd and user32.IsWindow(self._current_hwnd):
            user32.SetParent(self._current_hwnd, 0)
            user32.ShowWindow(self._current_hwnd, 0)  # SW_HIDE
        self._clear_scrcpy()
        self._current_hwnd = None

    def _sync_embed_size(self):
        self._update_container_size()
        if self._current_hwnd and user32.IsWindow(self._current_hwnd):
            w, h = self._embed_container.width(), self._embed_container.height()
            if w > 0 and h > 0:
                _resize_embedded(self._current_hwnd, w, h)
        if self._overlay:
            self._overlay.setGeometry(0, 0, self._embed_wrapper.width(), self._embed_wrapper.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._resize_timer.start(150)
