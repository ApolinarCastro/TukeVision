@echo off
setlocal

cd /d "%~dp0"
set "PYTHON=%~dp0.venv\Scripts\python.exe"
set "FIXTURE=%~dp0scripts\review_retention_fixture.py"
set "REVIEW=%~dp0scripts\review_behavior_signals.py"
set "TUKEVISION_REVIEW_ROOT=%~dp0data\runtime_evidence\_loop_0020_operator_review"

"%PYTHON%" "%FIXTURE%" prepare
if errorlevel 1 goto :failed

echo.
echo Verifique J=JPEG y C=clip; luego clasifique el caso con 1-5.
"%PYTHON%" "%REVIEW%"
if errorlevel 1 goto :failed

"%PYTHON%" "%FIXTURE%" verify-release
if errorlevel 1 goto :pending

echo.
echo LOOP-0020 OPERATOR RETENTION FLOW: PASS
pause
exit /b 0

:pending
echo.
echo La revision sigue pendiente; la evidencia permanece protegida.
pause
exit /b 3

:failed
echo.
echo LOOP-0020 OPERATOR FIXTURE: FAILED
pause
exit /b 1
