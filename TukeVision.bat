@echo off
setlocal
pushd "%~dp0"

set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "LAUNCHER=%~dp0scripts\launcher.py"

if not exist "%PYTHON%" (
    echo ERROR: No existe %PYTHON%
    pause
    exit /b 1
)

if not exist "%LAUNCHER%" (
    echo ERROR: No existe %LAUNCHER%
    pause
    exit /b 1
)

echo Iniciando TukeVision...
"%PYTHON%" -u "%LAUNCHER%"

set "CODE=%ERRORLEVEL%"
echo.
echo TukeVision finalizo con codigo: %CODE%

popd
pause
exit /b %CODE%
