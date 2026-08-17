@echo off
setlocal
cd /d "%~dp0"
set "BASE=%~dp0"
set "PYTHON=%BASE%.venv\Scripts\python.exe"
if not exist "%PYTHON%" (
  echo ERROR: BASE .venv Python no encontrado
  pause
  exit /b 1
)
if not exist "%BASE%scripts\review_behavior_signals.py" (
  echo ERROR: herramienta de revision no encontrada
  pause
  exit /b 1
)
"%PYTHON%" "%BASE%scripts\review_behavior_signals.py"
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" pause
endlocal & exit /b %CODE%
