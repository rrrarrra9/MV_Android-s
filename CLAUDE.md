# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Running the app

```bash
python main.py
# or on Windows:
iniciar.bat
```

Requires Python 3.10+ and PyQt6 (`pip install PyQt6`). On first run, a setup wizard downloads JDK 17, Android SDK cmdline-tools, platform-tools, emulator, and scrcpy automatically into `sdk/` and `tools/`.

## Architecture

**Entry point:** `main.py` checks `sdk_ready()` and `scrcpy_ready()` — if either fails, shows the `SetupWizard` before opening `MainWindow`.

**Two layers:**
- `core/` — business logic with no Qt UI: path resolution (`paths.py`), AVD management (`avd.py`), emulator/scrcpy processes (`emulator.py`), first-run installation (`setup.py`).
- `ui/` — PyQt6 widgets: `MainWindow`, `DevicePanel`, `ScreenView`, `LogBar`, `CreateAvdDialog`, `SetupWizard`.

**Emulator launch flow:**
1. `MainWindow._launch_avd()` starts `EmulatorLaunchThread` (in `core/emulator.py`).
2. Thread reads stdout until "boot completed", then calls `_find_serial()` which polls `adb devices` with retries until the device is online.
3. Thread emits `booted(avd_name, serial)` → `MainWindow._on_booted()` → `ScreenView.attach_serial()`.
4. `ScreenView` starts `ScrcpyEmbedThread`, which launches scrcpy off-screen (`--window-x -4000 --window-y -4000`).
5. The thread finds the scrcpy HWND by window title (`scrcpy_{avd_name}`), then `embed_window()` reparents it into `_embed_container` via WinAPI `SetParent`.

**Window embedding (Windows-only WinAPI):**
- `embed_window()` in `core/emulator.py` strips popup/caption styles, adds `WS_CHILD`, calls `SetParent(hwnd, container_hwnd)`, then `_resize_embedded()` which does `SetWindowPos` + sends `WM_SIZE` so SDL redraws scaled.
- `GetWindowLongW`/`SetWindowLongW` must use `restype = c_long` and values wrapped in `ctypes.c_long()` to avoid OverflowError on high-bit style flags.
- `ScreenView._embed_container` is sized to a 9:19.5 phone aspect ratio, centered inside `_embed_wrapper` with black sidebars.

**Tool paths** are all resolved relative to the repo root in `core/paths.py`:
- `sdk/` — Android SDK (emulator, adb, avdmanager, sdkmanager)
- `tools/scrcpy/` — scrcpy 3.1
- `tools/jdk/` — portable JDK 17 (Adoptium Temurin)

AVDs are stored in `~/.android/avd/` (standard Android location).

**Threading:** All long-running operations use `QThread` subclasses that emit signals. Never call Qt UI methods from worker threads directly.
