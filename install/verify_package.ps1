# verify_package.ps1 - Verifica la integridad del paquete portable
#
# Valida: MANIFEST, modelo, hash del modelo, requirements, archivos criticos.
# No ejecuta codigo principal.
#
# Uso:
#     powershell.exe -ExecutionPolicy Bypass -File install\verify_package.ps1
#     powershell.exe -ExecutionPolicy Bypass -File install\verify_package.ps1 -PackageDir "D:\TukeVision\dist\TukeVision"

param(
    [string]$PackageDir = ""
)

$ErrorActionPreference = "Continue"

function Write-Field([string]$Name, [string]$Value) {
    Write-Output ("{0}: {1}" -f $Name, $Value)
}

$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptPath

if (-not $PackageDir) {
    $PackageDir = Join-Path $ProjectRoot "dist\TukeVision"
}
$PackageDir = [System.IO.Path]::GetFullPath($PackageDir)

$fail = $false

Write-Field "PACKAGE_DIR" $PackageDir

# --- MANIFEST ----------------------------------------------------------------
$manifestPath = Join-Path $PackageDir "MANIFEST.json"
$manifestValid = "NO"
if (Test-Path -LiteralPath $manifestPath) {
    try {
        $m = Get-Content -LiteralPath $manifestPath -Raw | ConvertFrom-Json
        if ($m.package_version -and $m.git_head -and $m.spec_certified_base -and $m.model_sha256 -and $m.requirements_sha256) {
            $manifestValid = "YES"
        }
    } catch { }
}
Write-Field "MANIFEST_VALID" $manifestValid
if ($manifestValid -ne "YES") { $fail = $true }

# --- Modelo y hash --------------------------------------------------------------
$modelPath = Join-Path $PackageDir "models\yolo11n.pt"
$modelPresent = "NO"
$modelHashOk = "NO"
$expected = "0EBBC80D4A7680D14987A577CD21342B65ECFD94632BD9A8DA63AE6417644EE1"
if (Test-Path -LiteralPath $modelPath) {
    $modelPresent = "YES"
    $actual = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash
    if ($actual -eq $expected) { $modelHashOk = "YES" }
}
Write-Field "MODEL_PRESENT" $modelPresent
Write-Field "MODEL_HASH_VALID" $modelHashOk
if ($modelPresent -ne "YES" -or $modelHashOk -ne "YES") { $fail = $true }

# --- Requirements ----------------------------------------------------------------
foreach ($req in @("requirements.txt", "requirements.lock.txt")) {
    $p = Join-Path $PackageDir $req
    $present = "NO"
    if (Test-Path -LiteralPath $p) { $present = "YES" }
    Write-Field ("REQ_" + ($req -replace "\.", "_").ToUpper()) $present
    if ($present -ne "YES") { $fail = $true }
}

# --- Archivos criticos --------------------------------------------------------------
foreach ($crit in @("src\app\pipeline.py", "src\ui\tk_view.py", "src\ui\controller.py", "scripts\run_interface.py", "config\default.json", "start_tukevision.ps1", "install\install.ps1", "install\preflight.ps1", "install\diagnose.ps1")) {
    $p = Join-Path $PackageDir $crit
    $present = "NO"
    if (Test-Path -LiteralPath $p) { $present = "YES" }
    Write-Field ("FILE_" + ($crit -replace "\\", "_" -replace "\W", "_")) $present
    if ($present -ne "YES") { $fail = $true }
}

# --- Exclusiones ----------------------------------------------------------------------
foreach ($excluded in @(".git", ".venv", "tests", "data\input\Video.mp4", "data\output\processed.mp4", "data\temp\test_person.jpg")) {
    $p = Join-Path $PackageDir $excluded
    $absent = "OK"
    if (Test-Path -LiteralPath $p) { $absent = "PRESENT_UNEXPECTED"; $fail = $true }
    Write-Field ("EXCLUDE_" + ($excluded -replace "\\", "_" -replace "\W", "_")) $absent
}

Write-Output ""
if ($fail) {
    Write-Field "VERIFY_STATUS" "FAILED"
    exit 1
}
Write-Field "VERIFY_STATUS" "OK"
exit 0
