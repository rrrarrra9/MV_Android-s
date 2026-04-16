# Android Emulator Manager

Gestor de emuladores Android con interfaz gráfica para Windows. Diseñado para desarrolladores de **Expo / React Native** que necesitan crear, lanzar y depurar AVDs sin tocar la línea de comandos.

## Requisitos

- Windows 10/11 (64-bit)
- Python 3.10 o superior
- PyQt6

```bash
pip install PyQt6
```

> El SDK de Android, JDK 17 y scrcpy se descargan **automáticamente** en el primer arranque.

---

## Instalación

```bash
git clone https://github.com/rrrarrra9/MV_Android-s.git
cd MV_Android-s
pip install PyQt6
python main.py
```

O en Windows directamente:

```
iniciar.bat
```

La primera vez aparece un asistente que descarga todo lo necesario en la carpeta `sdk/` y `tools/`. Solo hay que esperar.

---

## Uso

### Crear una máquina virtual

1. En el panel izquierdo, haz clic en **+**
2. Elige nombre, versión de Android y tipo de dispositivo
3. Haz clic en **Crear**

### Iniciar / detener

- **▶** — lanza el emulador (aparece la pantalla del teléfono integrada en la ventana)
- **■** — apaga el emulador
- El indicador de estado muestra `⟳ Iniciando...` mientras arranca y `● En ejecución` cuando está listo

### Cambiar RAM

Haz clic en el botón **RAM** de la VM para ajustar la memoria (512 MB – 16 GB). Hay accesos rápidos de 1G, 2G, 4G, 6G y 8G.

### Eliminar una VM

Haz clic en **🗑** y confirma. Se borran la VM y todos sus datos.

### Ejecutar comandos ADB

En la barra superior hay un campo de texto para comandos ADB. Si tienes una VM seleccionada, el comando se dirige a ella automáticamente.

Ejemplos:
```
shell getprop ro.build.version.release
install /ruta/a/mi-app.apk
logcat -s ReactNativeJS
```

Pulsa **Enter** o el botón **ADB ▶** para ejecutar. La salida aparece en la barra de log inferior.

---

## Estructura del proyecto

```
main.py              # Entrada — verifica SDK y abre la ventana principal
iniciar.bat          # Lanzador para Windows
core/
  paths.py           # Rutas al SDK, JDK y scrcpy
  avd.py             # Gestión de AVDs (crear, listar, borrar)
  emulator.py        # Arranque del emulador y embedding de scrcpy
  setup.py           # Instalación automática en primer arranque
ui/
  main_window.py     # Ventana principal
  device_panel.py    # Panel izquierdo con lista de VMs
  screen_view.py     # Vista embebida del emulador
  log_bar.py         # Barra de log inferior
  create_avd_dialog.py
  setup_wizard.py
  theme.py
```

---

## Notas

- La carpeta `sdk/` y `tools/` se generan localmente y no están en el repositorio. Si las borras, el asistente de configuración las vuelve a crear al arrancar.
- Solo compatible con Windows (usa WinAPI para embeber la ventana de scrcpy).
