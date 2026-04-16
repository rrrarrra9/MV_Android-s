import shutil
from pathlib import Path

BASE_DIR = Path(__file__).parent.parent
SDK_DIR = BASE_DIR / "sdk"
TOOLS_DIR = BASE_DIR / "tools"
SCRCPY_DIR = TOOLS_DIR / "scrcpy"
JDK_DIR = TOOLS_DIR / "jdk"

CMDLINE_TOOLS = SDK_DIR / "cmdline-tools" / "latest" / "bin"
SDKMANAGER = CMDLINE_TOOLS / "sdkmanager.bat"
AVDMANAGER = CMDLINE_TOOLS / "avdmanager.bat"
EMULATOR = SDK_DIR / "emulator" / "emulator.exe"
ADB = SDK_DIR / "platform-tools" / "adb.exe"
SCRCPY_EXE = SCRCPY_DIR / "scrcpy.exe"

CMDLINE_TOOLS_URL = "https://dl.google.com/android/repository/commandlinetools-win-11076708_latest.zip"
SCRCPY_URL = "https://github.com/Genymobile/scrcpy/releases/download/v3.1/scrcpy-win64-v3.1.zip"
# Adoptium Temurin 17 - JDK portable para Windows x64
JDK_URL = "https://github.com/adoptium/temurin17-binaries/releases/download/jdk-17.0.11%2B9/OpenJDK17U-jdk_x64_windows_hotspot_17.0.11_9.zip"

SDK_PACKAGES = [
    "platform-tools",
    "emulator",
    "system-images;android-35;google_apis_playstore;x86_64",
    "system-images;android-34;google_apis_playstore;x86_64",
]

DEFAULT_IMAGE = "system-images;android-34;google_apis_playstore;x86_64"


def find_java() -> str | None:
    """Return path to java.exe: bundled JDK > IntelliJ > PATH > common installs."""
    # 1. JDK descargado por nosotros
    bundled = JDK_DIR / "bin" / "java.exe"
    if bundled.exists():
        return str(bundled)

    # 2. IntelliJ JBR
    ij_base = Path.home() / "AppData/Local/Programs"
    for ij_dir in ij_base.glob("IntelliJ*"):
        jbr = ij_dir / "jbr" / "bin" / "java.exe"
        if jbr.exists():
            return str(jbr)

    # 3. Android Studio JDK
    for as_dir in [
        Path.home() / "AppData/Local/Android/Sdk" / "..\\jre",
        Path("C:/Program Files/Android/Android Studio/jbr/bin"),
        Path("C:/Program Files/Android/Android Studio/jre/bin"),
    ]:
        j = Path(as_dir) / "java.exe"
        if j.exists():
            return str(j)

    # 4. Common JDK installs
    for base in [
        Path("C:/Program Files/Java"),
        Path("C:/Program Files/Eclipse Adoptium"),
        Path("C:/Program Files/Microsoft"),
        Path("C:/Program Files/OpenJDK"),
        Path(Path.home() / "AppData/Local/Programs"),
    ]:
        if base.exists():
            for sub in base.iterdir():
                j = sub / "bin" / "java.exe"
                if j.exists():
                    return str(j)

    # 5. PATH
    return shutil.which("java")
