"""Downloads and installs SDK cmdline-tools, JDK and scrcpy on first run."""
import os
import shutil
import zipfile
import urllib.request
from pathlib import Path
from PyQt6.QtCore import QThread, pyqtSignal
from core.paths import (
    SDK_DIR, TOOLS_DIR, SCRCPY_DIR, JDK_DIR,
    SDKMANAGER, EMULATOR, ADB, SCRCPY_EXE,
    CMDLINE_TOOLS_URL, SCRCPY_URL, JDK_URL,
    SDK_PACKAGES, find_java,
)


def sdk_ready():
    return SDKMANAGER.exists() and EMULATOR.exists() and ADB.exists()


def scrcpy_ready():
    return SCRCPY_EXE.exists()


def java_ready():
    return find_java() is not None


def sdk_env():
    """Build an os.environ copy with JAVA_HOME, ANDROID_HOME, etc. set."""
    java = find_java()
    env = os.environ.copy()
    env["ANDROID_HOME"] = str(SDK_DIR)
    env["ANDROID_SDK_ROOT"] = str(SDK_DIR)
    if java:
        java_home = str(Path(java).parent.parent)
        env["JAVA_HOME"] = java_home
        env["PATH"] = str(Path(java).parent) + os.pathsep + env.get("PATH", "")
    env["JAVA_OPTS"] = "-Xmx512m"
    return env


def _download(url, dest, progress_cb=None):
    dest = Path(dest)
    dest.parent.mkdir(parents=True, exist_ok=True)

    def _reporthook(count, block_size, total_size):
        if progress_cb and total_size > 0:
            pct = min(100, int(count * block_size * 100 / total_size))
            progress_cb(pct)

    urllib.request.urlretrieve(url, dest, reporthook=_reporthook)
    return dest


def _extract(zip_path, dest):
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(zip_path, "r") as z:
        z.extractall(dest)


def install_jdk(log, progress):
    log("Descargando JDK 17 portable (~180 MB)...")
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = TOOLS_DIR / "jdk.zip"
    _download(JDK_URL, zip_path, progress_cb=lambda p: progress(int(p * 0.9)))

    log("Extrayendo JDK...")
    tmp = TOOLS_DIR / "_tmp_jdk"
    _extract(zip_path, tmp)
    zip_path.unlink()

    if JDK_DIR.exists():
        shutil.rmtree(JDK_DIR)

    folders = [f for f in tmp.iterdir() if f.is_dir()]
    if folders:
        shutil.move(str(folders[0]), str(JDK_DIR))
    else:
        shutil.move(str(tmp), str(JDK_DIR))

    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)

    progress(100)
    log(f"JDK instalado en {JDK_DIR}")


def install_cmdline_tools(log, progress):
    log("Descargando Android cmdline-tools...")
    SDK_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = SDK_DIR / "cmdline-tools.zip"
    _download(CMDLINE_TOOLS_URL, zip_path, progress_cb=lambda p: progress(int(p * 0.9)))

    log("Extrayendo cmdline-tools...")
    tmp = SDK_DIR / "_tmp_cmdline"
    _extract(zip_path, tmp)
    zip_path.unlink()

    target = SDK_DIR / "cmdline-tools" / "latest"
    if target.exists():
        shutil.rmtree(target)
    target.parent.mkdir(parents=True, exist_ok=True)

    extracted = tmp / "cmdline-tools"
    if extracted.exists():
        shutil.move(str(extracted), str(target))
    else:
        shutil.move(str(tmp), str(target))

    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)

    progress(100)
    log("cmdline-tools instalado.")


def install_scrcpy(log, progress):
    log("Descargando scrcpy...")
    TOOLS_DIR.mkdir(parents=True, exist_ok=True)
    zip_path = TOOLS_DIR / "scrcpy.zip"
    _download(SCRCPY_URL, zip_path, progress_cb=lambda p: progress(int(p * 0.9)))

    log("Extrayendo scrcpy...")
    tmp = TOOLS_DIR / "_tmp_scrcpy"
    _extract(zip_path, tmp)
    zip_path.unlink()

    if SCRCPY_DIR.exists():
        shutil.rmtree(SCRCPY_DIR)

    folders = [f for f in tmp.iterdir() if f.is_dir()]
    if folders:
        shutil.move(str(folders[0]), str(SCRCPY_DIR))
    else:
        shutil.move(str(tmp), str(SCRCPY_DIR))

    if tmp.exists():
        shutil.rmtree(tmp, ignore_errors=True)

    progress(100)
    log("scrcpy instalado.")


def install_sdk_packages(log, progress, packages):
    import subprocess
    env = sdk_env()

    for i, pkg in enumerate(packages):
        log(f"Instalando {pkg}...")
        proc = subprocess.Popen(
            [str(SDKMANAGER), "--sdk_root=" + str(SDK_DIR), pkg],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            env=env,
        )
        proc.stdin.write("y\n")
        proc.stdin.flush()
        proc.stdin.close()
        for line in proc.stdout:
            line = line.strip()
            if line:
                log(line)
        rc = proc.wait()
        pct = int((i + 1) / len(packages) * 100)
        progress(pct)
        if rc == 0:
            log(f"OK: {pkg}")
        else:
            log(f"AVISO: {pkg} finalizó con código {rc}")


class SetupWorker(QThread):
    log = pyqtSignal(str)
    progress = pyqtSignal(int)
    stage = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, install_images=False, image_pkg=None):
        super().__init__()
        self.install_images = install_images
        self.image_pkg = image_pkg

    def run(self):
        try:
            if not java_ready():
                self.stage.emit("Descargando JDK 17...")
                install_jdk(self.log.emit, self.progress.emit)

            if not SDKMANAGER.exists():
                self.stage.emit("Descargando Android SDK tools...")
                install_cmdline_tools(self.log.emit, self.progress.emit)

            if not scrcpy_ready():
                self.stage.emit("Descargando scrcpy...")
                install_scrcpy(self.log.emit, self.progress.emit)

            self.stage.emit("Instalando platform-tools y emulador...")
            install_sdk_packages(self.log.emit, self.progress.emit, ["platform-tools", "emulator"])

            if self.install_images and self.image_pkg:
                self.stage.emit("Instalando imagen del sistema...")
                install_sdk_packages(self.log.emit, self.progress.emit, [self.image_pkg])

            self.finished.emit(True, "")
        except Exception as e:
            import traceback
            self.log.emit(traceback.format_exc())
            self.finished.emit(False, str(e))
