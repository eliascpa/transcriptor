@echo off
setlocal
cd /d "%~dp0"
title Transcriptor
if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta instalar.bat
    pause
    exit /b 1
)
echo ============================================
echo   Transcriptor
echo   Se abrira en el navegador: http://127.0.0.1:7860
echo   Para cerrar la aplicacion, cierra esta ventana.
echo ============================================
echo.
".venv\Scripts\python.exe" app.py
echo.
echo La aplicacion se detuvo.
pause
