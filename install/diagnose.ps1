# diagnose.ps1 - Diagnostico del entorno TukeVision
#
# Verifica: Python, venv, imports, modelo, hash, config, directorios de datos,
# webcam basica (maximo 3 frames), permisos de escritura.
#
# No ejecuta YOLO sobre video largo.
#
# Uso:
#     powershell.exe -ExecutionPolicy Bypass -File install\diagnose.ps1

$ErrorActionPreference = "Continue"
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptPath

function Write-Field([string]$Name, [string]$Value) {
    Write-Output ("{0}: {1}" -f $Name, $Value)
}

# --- Python y venv ----------------------------------------------------------------
$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$venvStatus = "MISSING"
if (Test-Path -LiteralPath $venvPython) {
    $venvStatus = "PRESENT"
}
Write-Field "VENV_STATUS" $venvStatus

$pyVersion = "NOT_FOUND"
if ($venvStatus -eq "PRESENT") {
    try { $pyVersion = & $venvPython -c "import sys; print(sys.version.split()[0])" 2>&1 | Select-Object -Last 1 } catch { }
}
Write-Field "PYTHON" $pyVersion

# --- Imports -------------------------------------------------------------------------
$importStatus = "FAIL"
$missingImports = @()
if ($venvStatus -eq "PRESENT") {
    foreach ($mod in @("cv2", "ultralytics", "supervision", "trackers", "tkinter")) {
        & $venvPython -c ("import {0}" -f $mod) 2>&1 | Out-Null
        if ($LASTEXITCODE -ne 0) { $missingImports += $mod }
    }
    if ($missingImports.Count -eq 0) { $importStatus = "OK" }
}
Write-Field "IMPORTS" $importStatus
if ($missingImports.Count -gt 0) {
    Write-Field "IMPORTS_MISSING" ($missingImports -join ",")
}

# --- Modelo y hash --------------------------------------------------------------------
$modelPath = Join-Path $ProjectRoot "models\yolo11n.pt"
$modelPresent = "NO"
$modelHashOk = "NO"
if (Test-Path -LiteralPath $modelPath) {
    $modelPresent = "YES"
    $expected = "0EBBC80D4A7680D14987A577CD21342B65ECFD94632BD9A8DA63AE6417644EE1"
    $actual = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash
    if ($actual -eq $expected) { $modelHashOk = "YES" }
}
Write-Field "MODEL_PRESENT" $modelPresent
Write-Field "MODEL_HASH_VALID" $modelHashOk

# --- Config ------------------------------------------------------------------------------
$configPath = Join-Path $ProjectRoot "config\default.json"
if (Test-Path -LiteralPath $configPath) { Write-Field "CONFIG_PRESENT" "YES" }
else { Write-Field "CONFIG_PRESENT" "NO" }

# --- Directorios de datos ---------------------------------------------------------------
foreach ($dir in @("data\input", "data\output", "data\evidence", "data\temp", "logs")) {
    $field = "DIR_" + ($dir -replace "\\", "_").ToUpper()
    if (Test-Path -LiteralPath (Join-Path $ProjectRoot $dir)) { Write-Field $field "YES" }
    else { Write-Field $field "NO" }
}

# --- Permisos de escritura ----------------------------------------------------------------
$writeOk = "NO"
try {
    $probe = Join-Path $ProjectRoot ".diagnose_write_probe"
    Set-Content -LiteralPath $probe -Value "probe" -ErrorAction Stop
    Remove-Item -LiteralPath $probe -Force -ErrorAction Stop
    $writeOk = "YES"
} catch { }
Write-Field "WRITE_ACCESS" $writeOk

# --- Webcam basica (maximo 3 frames, opcional) --------------------------------------------
Write-Field "WEBCAM_STATUS" "CHECKING"
if ($venvStatus -eq "PRESENT") {
    $webcamScript = @'
import sys
try:
    import cv2
except Exception:
    print("WEBCAM_STATUS: SKIPPED_IMPORT")
    sys.exit(0)
cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
if not cap.isOpened():
    cap = cv2.VideoCapture(0)
if not cap.isOpened():
    print("WEBCAM_STATUS: NOT_AVAILABLE")
    sys.exit(0)
frames = 0
for _ in range(3):
    ok, frame = cap.read()
    if ok:
        frames += 1
    else:
        break
cap.release()
if frames > 0:
    print("WEBCAM_STATUS: OK (frames=" + str(frames) + ")")
else:
    print("WEBCAM_STATUS: NOT_AVAILABLE")
'@
    $tmpScript = Join-Path $ProjectRoot ".diagnose_webcam_probe.py"
    Set-Content -LiteralPath $tmpScript -Value $webcamScript -Encoding UTF8
    try {
        & $venvPython $tmpScript 2>$null
        if ($LASTEXITCODE -ne 0) { Write-Field "WEBCAM_STATUS" "NOT_AVAILABLE" }
    } catch {
        Write-Field "WEBCAM_STATUS" "NOT_AVAILABLE"
    }
    Remove-Item -LiteralPath $tmpScript -Force -ErrorAction SilentlyContinue
} else {
    Write-Field "WEBCAM_STATUS" "NOT_AVAILABLE"
}

# --- RTSP --------------------------------------------------------------------------------------
Write-Field "RTSP_SUPPORT" "AVAILABLE"
Write-Field "RTSP_REAL_SOURCE" "NOT_CONFIGURED"

Write-Output ""
Write-Output "DIAGNOSE_STATUS: COMPLETED"
exit 0
