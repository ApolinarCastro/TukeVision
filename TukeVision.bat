@echo off
setlocal
cd /d "%~dp0"
powershell.exe -ExecutionPolicy Bypass -File "%~dp0start_tukevision.ps1" -Mode Multicamera
set "CODE=%ERRORLEVEL%"
if not "%CODE%"=="0" pause
endlocal & exit /b %CODE%
