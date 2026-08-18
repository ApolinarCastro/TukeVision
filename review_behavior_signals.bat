@echo off
setlocal

cd /d "%~dp0"

set "BASE=%~dp0"
set "PYTHON=%BASE%.venv\Scripts\python.exe"
set "REVIEW_SCRIPT=%BASE%scripts\review_behavior_signals.py"

echo ==========================================
echo        TUKEVISION - REVISION HUMANA
echo ==========================================
echo.

if not exist "%PYTHON%" (
    echo ERROR: BASE .venv Python no encontrado:
    echo %PYTHON%
    echo.
    pause
    exit /b 1
)

"%PYTHON%" --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: BASE .venv Python existe pero no puede ejecutarse.
    echo Repare el entorno local antes de iniciar la revision.
    echo.
    pause
    exit /b 1
)

if not exist "%REVIEW_SCRIPT%" (
    echo ERROR: herramienta de revision no encontrada:
    echo %REVIEW_SCRIPT%
    echo.
    pause
    exit /b 1
)

echo Iniciando herramienta de revision...
echo Controles: J abre JPEG, C abre clip, 1-5 clasifica, Q guarda.
echo.

"%PYTHON%" "%REVIEW_SCRIPT%"

set "CODE=%ERRORLEVEL%"

echo.
echo ==========================================
echo Revision finalizada.
echo Exit code: %CODE%
echo ==========================================
echo.

pause

endlocal & exit /b %CODE%
