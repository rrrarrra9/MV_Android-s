"""AVD management: list, create, delete."""
import os
import subprocess
from pathlib import Path
from core.paths import SDK_DIR, AVDMANAGER, ADB, EMULATOR


def _sdk_env():
    from core.setup import sdk_env
    env = sdk_env()
    env["ANDROID_AVD_HOME"] = str(Path.home() / ".android" / "avd")
    return env


def list_avds():
    avd_dir = Path.home() / ".android" / "avd"
    if not avd_dir.exists():
        return []
    avds = []
    for ini in avd_dir.glob("*.ini"):
        if ini.stem != "":
            avds.append(ini.stem)
    return sorted(avds)


def get_avd_info(name):
    avd_dir = Path.home() / ".android" / "avd" / f"{name}.avd"
    config = avd_dir / "config.ini"
    info = {"name": name, "api": "?", "device": "?", "ram": "?", "abi": "?"}
    if config.exists():
        with open(config, encoding="utf-8", errors="ignore") as f:
            for line in f:
                if "=" in line:
                    k, v = line.strip().split("=", 1)
                    if k == "image.sysdir.1":
                        parts = v.split("/")
                        for p in parts:
                            if p.startswith("android-"):
                                info["api"] = p.replace("android-", "API ")
                    elif k == "hw.device.name":
                        info["device"] = v
                    elif k == "hw.ramSize":
                        info["ram"] = v + " MB"
                    elif k == "abi.type":
                        info["abi"] = v
    return info


def get_avd_ram(name):
    """Return hw.ramSize from config.ini, or None if not found."""
    config = Path.home() / ".android" / "avd" / f"{name}.avd" / "config.ini"
    if not config.exists():
        return None
    with open(config, encoding="utf-8", errors="ignore") as f:
        for line in f:
            if line.startswith("hw.ramSize="):
                try:
                    return int(line.split("=", 1)[1].strip())
                except ValueError:
                    return None
    return None


def set_avd_ram(name, ram_mb):
    """Write hw.ramSize to an existing AVD's config.ini."""
    config = Path.home() / ".android" / "avd" / f"{name}.avd" / "config.ini"
    if not config.exists():
        return
    with open(config, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    new_lines = []
    written = False
    for line in lines:
        if line.startswith("hw.ramSize="):
            new_lines.append(f"hw.ramSize={ram_mb}\n")
            written = True
        else:
            new_lines.append(line)
    if not written:
        new_lines.append(f"hw.ramSize={ram_mb}\n")
    with open(config, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def create_avd(name, package, device, ram, storage, log_cb, finished_cb):
    from PyQt6.QtCore import QThread, pyqtSignal

    class Worker(QThread):
        output = pyqtSignal(str)
        done = pyqtSignal(bool, str)

        def run(self):
            env = _sdk_env()
            avd_home = Path.home() / ".android" / "avd"
            avd_home.mkdir(parents=True, exist_ok=True)

            # Install image first
            sdkmanager = SDK_DIR / "cmdline-tools" / "latest" / "bin" / "sdkmanager.bat"
            if sdkmanager.exists():
                self.output.emit(f"Instalando imagen {package}...")
                proc = subprocess.Popen(
                    [str(sdkmanager), "--sdk_root=" + str(SDK_DIR), package],
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    env=env
                )
                proc.stdin.write("y\n")
                proc.stdin.flush()
                proc.stdin.close()
                for line in proc.stdout:
                    line = line.strip()
                    if line:
                        self.output.emit(line)
                proc.wait()

            self.output.emit(f"Creando AVD '{name}'...")
            cmd = [
                str(AVDMANAGER), "create", "avd",
                "--name", name,
                "--package", package,
                "--device", device,
                "--force",
                "--path", str(avd_home / f"{name}.avd"),
            ]
            proc = subprocess.Popen(
                cmd,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                env=env
            )
            proc.stdin.write("no\n")
            proc.stdin.flush()
            proc.stdin.close()
            output = ""
            for line in proc.stdout:
                line = line.strip()
                if line:
                    self.output.emit(line)
                    output += line + "\n"
            proc.wait()

            if proc.returncode == 0:
                _apply_hardware_config(name, ram, storage)
                self.done.emit(True, "")
            else:
                self.done.emit(False, output)

    w = Worker()
    w.output.connect(log_cb)
    w.done.connect(finished_cb)
    w.start()
    return w


def _apply_hardware_config(name, ram_mb, storage_mb):
    config = Path.home() / ".android" / "avd" / f"{name}.avd" / "config.ini"
    if not config.exists():
        return
    with open(config, encoding="utf-8", errors="ignore") as f:
        lines = f.readlines()
    updates = {
        "hw.ramSize": str(ram_mb),
        "disk.dataPartition.size": f"{storage_mb}M",
        "hw.keyboard": "yes",
        "hw.gpu.enabled": "yes",
        "hw.gpu.mode": "auto",
        "fastboot.forceColdBoot": "no",
    }
    new_lines = []
    written = set()
    for line in lines:
        key = line.split("=")[0].strip() if "=" in line else None
        if key in updates:
            new_lines.append(f"{key}={updates[key]}\n")
            written.add(key)
        else:
            new_lines.append(line)
    for key, val in updates.items():
        if key not in written:
            new_lines.append(f"{key}={val}\n")
    with open(config, "w", encoding="utf-8") as f:
        f.writelines(new_lines)


def delete_avd(name):
    env = _sdk_env()
    subprocess.run(
        [str(AVDMANAGER), "delete", "avd", "--name", name],
        env=env,
        capture_output=True
    )
    avd_dir = Path.home() / ".android" / "avd"
    for ext in [".avd", ".ini"]:
        p = avd_dir / f"{name}{ext}"
        if p.exists():
            if p.is_dir():
                import shutil
                shutil.rmtree(p, ignore_errors=True)
            else:
                p.unlink()


def list_installed_images():
    images_dir = SDK_DIR / "system-images"
    found = []
    if not images_dir.exists():
        return found
    for android_ver in images_dir.iterdir():
        for variant in android_ver.iterdir():
            for abi in variant.iterdir():
                if (abi / "system.img").exists():
                    pkg = f"system-images;{android_ver.name};{variant.name};{abi.name}"
                    found.append(pkg)
    return found


def get_running_emulators():
    if not ADB.exists():
        return {}
    try:
        result = subprocess.run(
            [str(ADB), "devices"],
            capture_output=True, text=True, timeout=5,
            env=_sdk_env()
        )
        running = {}
        for line in result.stdout.splitlines()[1:]:
            parts = line.split()
            if len(parts) < 2:
                continue
            serial = parts[0]
            state = parts[1]
            if "emulator" not in serial:
                continue
            try:
                r = subprocess.run(
                    [str(ADB), "-s", serial, "emu", "avd", "name"],
                    capture_output=True, text=True, timeout=5,
                    env=_sdk_env()
                )
                avd_name = r.stdout.splitlines()[0].strip() if r.stdout.strip() else ""
                if avd_name:
                    running[avd_name] = serial
                elif state == "device":
                    running[serial] = serial
            except Exception:
                if state == "device":
                    running[serial] = serial
        return running
    except Exception:
        return {}
