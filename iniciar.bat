@echo off
cd /d "%~dp0"
python main.py
if %errorlevel% neq 0 (
    echo.
    echo Error al iniciar. Asegurate de tener Python 3.10+ instalado.
    pause
)
