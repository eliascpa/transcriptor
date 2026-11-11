@echo off
setlocal
cd /d "%~dp0"
title Instalar Transcriptor
echo ============================================
echo   Instalando Transcriptor (Windows)
echo ============================================
echo.

rem --- Buscar Python (preferir 3.12) ---
set "PY="
where py >nul 2>nul
if not errorlevel 1 (
    py -3.12 -c "import sys" >nul 2>nul
    if not errorlevel 1 (
        set "PY=py -3.12"
    ) else (
        set "PY=py -3"
    )
) else (
    where python >nul 2>nul
    if not errorlevel 1 set "PY=python"
)
if not defined PY (
    echo No se encontro Python.
    echo Instala Python 3.12 desde https://www.python.org/downloads/windows/
    echo y marca la casilla "Add python.exe to PATH". Luego vuelve a ejecutar este archivo.
    goto :error
)

%PY% -c "import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)"
if errorlevel 1 (
    echo Se necesita Python 3.10 o superior. Recomendado: Python 3.12.
    goto :error
)
echo Usando:
%PY% --version
echo.

rem --- Entorno virtual ---
if not exist ".venv\Scripts\python.exe" (
    echo Creando entorno virtual...
    %PY% -m venv .venv
    if errorlevel 1 goto :error
)

echo Instalando dependencias (puede tardar unos minutos)...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto :error
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 goto :error

echo.
echo ============================================
echo   Instalacion completa.
echo   Para abrir la aplicacion: doble clic en iniciar.bat
echo   Si tienes tarjeta NVIDIA: ejecuta instalar-gpu.bat (opcional)
echo ============================================
pause
exit /b 0

:error
echo.
echo *** La instalacion no se completo. Revisa los mensajes de arriba. ***
pause
exit /b 1
