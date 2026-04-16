"""Launch/stop emulator processes and embed scrcpy via WinAPI SetParent."""
import os
import subprocess
import ctypes
import ctypes.wintypes
import time
from PyQt6.QtCore import QThread, pyqtSignal, QTimer
from PyQt6.QtWidgets import QWidget
from PyQt6.QtGui import QWindow
from core.paths import SDK_DIR, EMULATOR, ADB, SCRCPY_EXE
from core import avd as avd_mod


def _sdk_env():
    from core.setup import sdk_env
    return sdk_env()


# ── WinAPI helpers ─────────────────────────────────────────────────────────────

GWL_STYLE = -16
GWL_EXSTYLE = -20
WS_CHILD = 0x40000000
WS_POPUP = 0x80000000
WS_CAPTION = 0x00C00000
WS_THICKFRAME = 0x00040000
WS_MINIMIZE = 0x20000000
WS_MAXIMIZE = 0x01000000
WS_SYSMENU = 0x00080000
WS_EX_TOOLWINDOW = 0x00000080
SWP_NOSIZE = 0x0001
SWP_NOMOVE = 0x0002
SWP_NOZORDER = 0x0004
SWP_FRAMECHANGED = 0x0020
SWP_SHOWWINDOW = 0x0040

user32 = ctypes.windll.user32


_EnumWindowsProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.wintypes.HWND, ctypes.wintypes.LPARAM)


def _find_window_by_pid(pid, timeout=30):
    """Poll until a top-level window owned by pid appears."""
    pid_buf = ctypes.c_ulong()
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = []

        def _cb(hwnd, _):
            user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid_buf))
            if pid_buf.value == pid and user32.IsWindowVisible(hwnd):
                found.append(hwnd)
                return False  # stop enumeration early
            return True

        user32.EnumWindows(_EnumWindowsProc(_cb), 0)
        if found:
            return found[0]
        time.sleep(1)
    return None


def _find_window_by_title_fragment(fragment, timeout=30):
    frag_lower = fragment.lower()
    buf = ctypes.create_unicode_buffer(512)
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = []

        def _cb(hwnd, _):
            user32.GetWindowTextW(hwnd, buf, 512)
            if frag_lower in buf.value.lower() and user32.IsWindowVisible(hwnd):
                found.append(hwnd)
                return False  # stop enumeration early
            return True

        user32.EnumWindows(_EnumWindowsProc(_cb), 0)
        if found:
            return found[0]
        if timeout <= 0.2:
            break
        time.sleep(1)
    return None


WM_SIZE = 0x0005
SIZE_RESTORED = 0


def embed_window(hwnd, container: QWidget):
    """Reparent an external HWND into a QWidget container."""
    parent_hwnd = int(container.winId())

    user32.GetWindowLongW.restype = ctypes.c_long
    user32.SetWindowLongW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int, ctypes.c_long]

    style = user32.GetWindowLongW(hwnd, GWL_STYLE)
    style = ctypes.c_long(
        style & ~(WS_POPUP | WS_CAPTION | WS_THICKFRAME | WS_MINIMIZE | WS_MAXIMIZE | WS_SYSMENU) | WS_CHILD
    ).value
    user32.SetWindowLongW(hwnd, GWL_STYLE, style)

    ex_style = user32.GetWindowLongW(hwnd, GWL_EXSTYLE)
    ex_style = ctypes.c_long(ex_style | WS_EX_TOOLWINDOW).value
    user32.SetWindowLongW(hwnd, GWL_EXSTYLE, ex_style)

    user32.SetParent(hwnd, parent_hwnd)

    w, h = container.width(), container.height()
    _resize_embedded(hwnd, w, h)
    user32.ShowWindow(hwnd, 1)


def _resize_embedded(hwnd, w, h):
    """Resize embedded window and notify SDL so it redraws scaled."""
    user32.MoveWindow(hwnd, 0, 0, w, h, True)
    user32.SetWindowPos(hwnd, 0, 0, 0, w, h, SWP_NOZORDER | SWP_FRAMECHANGED | SWP_SHOWWINDOW)
    # WM_SIZE lparam: HIWORD=height, LOWORD=width
    lparam = ctypes.c_long(((h & 0xFFFF) << 16) | (w & 0xFFFF)).value
    user32.SendMessageW(hwnd, WM_SIZE, SIZE_RESTORED, lparam)


# ── Emulator launch thread ─────────────────────────────────────────────────────

class EmulatorLaunchThread(QThread):
    log = pyqtSignal(str)
    booted = pyqtSignal(str, str)   # avd_name, adb_serial
    stopped = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, avd_name):
        super().__init__()
        self.avd_name = avd_name
        self._proc = None
        self._alive = True

    def run(self):
        env = _sdk_env()
        ram_mb = avd_mod.get_avd_ram(self.avd_name) or 2048
        cmd = [
            str(EMULATOR),
            "-avd", self.avd_name,
            "-no-snapshot-save",
            "-no-snapshot-load",
            "-gpu", "swiftshader_indirect",
            "-no-audio",
            "-no-boot-anim",
            "-no-window",
            "-memory", str(ram_mb),
            "-cores", "2",
        ]
        self.log.emit(f"Iniciando emulador: {self.avd_name}...")
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env
            )
        except Exception as e:
            self.error.emit(str(e))
            return

        booted = False
        batch = []
        last_flush = time.time()
        for line in self._proc.stdout:
            if not self._alive:
                break
            line = line.rstrip()
            if line:
                batch.append(line)
            now = time.time()
            if now - last_flush >= 0.5 and batch:
                self.log.emit("\n".join(batch))
                batch.clear()
                last_flush = now
            if not booted and line and ("boot completed" in line.lower() or "bootcomplete=1" in line.lower()):
                if batch:
                    self.log.emit("\n".join(batch))
                    batch.clear()
                serial = self._find_serial()
                if serial:
                    self.booted.emit(self.avd_name, serial)
                    booted = True
        if batch:
            self.log.emit("\n".join(batch))

        self._proc.wait()
        if self._alive and not booted:
            serial = self._find_serial()
            if serial:
                self.booted.emit(self.avd_name, serial)
        self.stopped.emit(self.avd_name)

    def _find_serial(self, retries=10, delay=2):
        for i in range(retries):
            try:
                running = avd_mod.get_running_emulators()
                serial = running.get(self.avd_name, "")
                if serial:
                    return serial
            except Exception:
                pass
            time.sleep(delay if i < 5 else delay * 1.5)
        return ""

    def stop(self):
        self._alive = False
        if self._proc:
            self._proc.terminate()


# ── Scrcpy embed thread ────────────────────────────────────────────────────────

class ScrcpyEmbedThread(QThread):
    log = pyqtSignal(str)
    hwnd_ready = pyqtSignal(int)
    stopped = pyqtSignal()

    def __init__(self, serial, title_hint, container_size=None):
        super().__init__()
        self.serial = serial
        self.title_hint = title_hint
        self.container_size = container_size  # (w, h) tuple or None
        self._proc = None
        self._alive = True

    def run(self):
        env = os.environ.copy()
        env["PATH"] = str(SCRCPY_EXE.parent) + ";" + env.get("PATH", "")
        env["ADB"] = str(ADB)

        window_title = f"scrcpy_{self.title_hint}"
        cmd = [
            str(SCRCPY_EXE),
            "--serial", self.serial,
            "--window-title", window_title,
            "--window-borderless",
            "--no-audio",
            "--stay-awake",
            "--turn-screen-off",
            "--window-x", "-4000",
            "--window-y", "-4000",
        ]
        if self.container_size:
            w, h = self.container_size
            if w > 0 and h > 0:
                cmd += ["--window-width", str(w), "--window-height", str(h)]
        self.log.emit(f"Conectando scrcpy a {self.serial}...")
        try:
            self._proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env
            )
        except Exception as e:
            self.log.emit(f"Error scrcpy: {e}")
            return

        hwnd_found = False
        batch = []
        last_flush = time.time()
        for line in self._proc.stdout:
            if not self._alive:
                break
            line = line.rstrip()
            if line:
                batch.append(f"[scrcpy] {line}")
            now = time.time()
            if now - last_flush >= 1.0 and batch:
                self.log.emit("\n".join(batch))
                batch.clear()
                last_flush = now
            if not hwnd_found:
                hwnd = _find_window_by_title_fragment(window_title, timeout=0)
                if hwnd:
                    if batch:
                        self.log.emit("\n".join(batch))
                        batch.clear()
                    self.hwnd_ready.emit(hwnd)
                    hwnd_found = True
        if batch:
            self.log.emit("\n".join(batch))

        if not hwnd_found:
            hwnd = _find_window_by_title_fragment(window_title, timeout=5)
            if hwnd:
                self.hwnd_ready.emit(hwnd)

        self._proc.wait()
        self.stopped.emit()

    def stop(self):
        self._alive = False
        if self._proc:
            self._proc.terminate()


def wait_for_boot(serial, log_cb, timeout=120):
    """Poll ADB until boot_completed=1."""
    env = _sdk_env()
    deadline = time.time() + timeout
    while time.time() < deadline:
        try:
            r = subprocess.run(
                [str(ADB), "-s", serial, "shell", "getprop", "sys.boot_completed"],
                capture_output=True, text=True, timeout=5, env=env
            )
            if r.stdout.strip() == "1":
                return True
        except Exception:
            pass
        log_cb("Esperando que el emulador arranque...")
        time.sleep(3)
    return False
