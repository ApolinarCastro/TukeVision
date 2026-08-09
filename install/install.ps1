# install.ps1 - Instalacion de TukeVision en entorno virtual
#
# Flujo:
#   preflight -> crear .venv -> actualizar pip (opcional) ->
#   instalar requirements.txt -> pip check -> verificar imports ->
#   verificar modelo -> diagnostico -> resultado
#
# Uso:
#     powershell.exe -ExecutionPolicy Bypass -File install\install.ps1
#
# No usa Python global para dependencias. No instala paquetes sueltos.

param(
    [switch]$SkipPreflight,
    [switch]$UpgradePip
)

$ErrorActionPreference = "Continue"
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptPath

function Write-Step([string]$Name) {
    Write-Output ""
    Write-Output ("==== {0} ====" -f $Name)
}

function Find-Python312 {
    # Devuelve el comando python 3.12.x preferido (py -3.12 o python)
    if (Get-Command py -ErrorAction SilentlyContinue) {
        try {
            $v = & py -3.12 -c "import sys; print(sys.version.split()[0])" 2>$null
            if ($LASTEXITCODE -eq 0 -and $v -match "3\.12\.\d+") {
                return "py -3.12"
            }
        } catch { }
    }
    if (Get-Command python -ErrorAction SilentlyContinue) {
        try {
            $v = & python -c "import sys; print(sys.version.split()[0])" 2>$null
            if ($LASTEXITCODE -eq 0 -and $v -match "3\.12\.\d+") {
                return "python"
            }
        } catch { }
    }
    return $null
}

# --- 1. preflight ---------------------------------------------------------------
if (-not $SkipPreflight) {
    Write-Step "PREFLIGHT"
    & powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ScriptPath "preflight.ps1")
    if ($LASTEXITCODE -ne 0) {
        Write-Output "ERROR: preflight fall"
        exit 1
    }
}

$pythonCmd = Find-Python312
if (-not $pythonCmd) {
    Write-Output "ERROR: Python 3.12.x requerido"
    Write-Output "PYTHON_312_REQUIRED"
    exit 1
}
Write-Output ("Python detectado: " + $pythonCmd)

# --- 2. crear .venv ---------------------------------------------------------------
Write-Step "CREAR .VENV"
$venvPath = Join-Path $ProjectRoot ".venv"
if (-not (Test-Path -LiteralPath (Join-Path $venvPath "Scripts\python.exe"))) {
    if ($pythonCmd -eq "py -3.12") {
        & py -3.12 -m venv $venvPath
    } else {
        & python -m venv $venvPath
    }
    if ($LASTEXITCODE -ne 0) {
        Write-Output "ERROR: no se pudo crear el entorno virtual"
        exit 1
    }
    Write-Output ".venv creado"
} else {
    Write-Output ".venv ya existe"
}

$venvPython = Join-Path $venvPath "Scripts\python.exe"
if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Output "ERROR: python del venv no encontrado"
    exit 1
}
& $venvPython --version

# --- 3. actualizar pip (opcional) ---------------------------------------------------
Write-Step "PIP"
if ($UpgradePip) {
    Write-Output "Actualizando pip (solicitado)"
    & $venvPython -m pip install --upgrade pip
} else {
    Write-Output "pip no actualizado (use -UpgradePip para hacerlo)"
}

# --- 4. instalar requirements.txt ------------------------------------------------------
Write-Step "INSTALAR REQUIREMENTS.TXT"
$reqTxt = Join-Path $ProjectRoot "requirements.txt"
if (-not (Test-Path -LiteralPath $reqTxt)) {
    Write-Output "ERROR: requirements.txt no encontrado"
    exit 1
}
& $venvPython -m pip install -r $reqTxt
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: fallo al instalar dependencias"
    Write-Output "BLOCKED_BY_DEPENDENCY"
    exit 1
}

# --- 5. pip check ---------------------------------------------------------------------
Write-Step "PIP CHECK"
& $venvPython -m pip check
if ($LASTEXITCODE -ne 0) {
    Write-Output "ERROR: pip check reporto dependencias rotas"
    exit 1
}

# --- 6. verificar imports ---------------------------------------------------------------
Write-Step "VERIFICAR IMPORTS"
$imports = @("cv2", "ultralytics", "supervision", "trackers", "tkinter")
$importFail = $false
foreach ($mod in $imports) {
    & $venvPython -c ("import {0}" -f $mod) 2>&1 | Out-Null
    if ($LASTEXITCODE -eq 0) {
        Write-Output ("  OK  " + $mod)
    } else {
        Write-Output ("  FAIL " + $mod)
        $importFail = $true
    }
}
if ($importFail) {
    Write-Output "ERROR: imports criticos fallaron"
    exit 1
}

# --- 7. verificar modelo ------------------------------------------------------------------
Write-Step "VERIFICAR MODELO"
$modelPath = Join-Path $ProjectRoot "models\yolo11n.pt"
if (-not (Test-Path -LiteralPath $modelPath)) {
    Write-Output "ERROR: modelo no encontrado"
    Write-Output "MODEL_MISSING"
    exit 1
}
$expected = "0EBBC80D4A7680D14987A577CD21342B65ECFD94632BD9A8DA63AE6417644EE1"
$actual = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash
Write-Output ("esperado: " + $expected)
Write-Output ("actual:   " + $actual)
if ($actual -ne $expected) {
    Write-Output "ERROR: hash del modelo no coincide"
    Write-Output "MODEL_HASH_MISMATCH"
    exit 1
}
Write-Output "MODEL_HASH_OK"

# --- 8. diagnostico ---------------------------------------------------------------------------
Write-Step "DIAGNOSTICO"
& powershell.exe -NoProfile -ExecutionPolicy Bypass -File (Join-Path $ScriptPath "diagnose.ps1")
if ($LASTEXITCODE -ne 0) {
    Write-Output "ADVERTENCIA: el diagnostico reporto problemas no bloqueantes"
}

# --- 9. resultado -------------------------------------------------------------------------------
Write-Step "RESULTADO"
Write-Output "INSTALL_STATUS: OK"
Write-Output "Para iniciar la interfaz:"
Write-Output "  powershell.exe -ExecutionPolicy Bypass -File start_tukevision.ps1"
exit 0
