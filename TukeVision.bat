@echo off
setlocal
cd /d "%~dp0"
REM Launcher with secure credential dialog
"%~dp0.venv\Scripts\python.exe" "%~dp0scripts\launcher.py"
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" pause
endlocal & exit /b %CODE%
