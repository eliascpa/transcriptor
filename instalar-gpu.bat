@echo off
setlocal
cd /d "%~dp0"
title Activar GPU NVIDIA - Transcriptor
echo ============================================
echo   Aceleracion con tarjeta NVIDIA (opcional)
echo ============================================
echo.
echo Requisitos: tarjeta NVIDIA y controlador (driver) actualizado.
echo Descarga las bibliotecas CUDA 12 / cuDNN 9 (~1-2 GB).
echo.

if not exist ".venv\Scripts\python.exe" (
    echo Primero ejecuta instalar.bat
    goto :error
)

where nvidia-smi >nul 2>nul
if errorlevel 1 (
    echo No se detecto una tarjeta NVIDIA ^(nvidia-smi no encontrado^).
    echo La aplicacion funcionara con el procesador ^(CPU^); no hace falta este paso.
    goto :error
)
nvidia-smi --query-gpu=name,driver_version --format=csv,noheader
echo.

".venv\Scripts\python.exe" -m pip install nvidia-cublas-cu12 "nvidia-cudnn-cu12>=9,<10"
if errorlevel 1 goto :error

echo.
echo Comprobando la GPU...
".venv\Scripts\python.exe" -c "import motor_faster as m; print('Motor:', m.describe())"

echo.
echo Listo. Si la aplicacion falla al transcribir con GPU, se cambiara sola a CPU.
echo Para forzar CPU: set TRANSCRIPTOR_DEVICE=cpu antes de iniciar.bat
pause
exit /b 0

:error
echo.
pause
exit /b 1
