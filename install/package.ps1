# package.ps1 - Genera el paquete portable de TukeVision
#
# Genera dist/TukeVision/ con nicamente lo necesario y opcionalmente
# dist/TukeVision-portable.zip.
#
# Uso:
#     powershell.exe -ExecutionPolicy Bypass -File install\package.ps1
#
# Parmetros:
#     -NoZip  : no generar el archivo comprimido.

param(
    [switch]$NoZip
)

$ErrorActionPreference = "Continue"
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptPath

$PackageVersion = "0.1.0"

function Write-Step([string]$Name) {
    Write-Output ("==== {0} ====" -f $Name)
}

Write-Step "DETERMINAR GIT HEAD"
$gitHead = "UNKNOWN"
if (Get-Command git -ErrorAction SilentlyContinue) {
    try { $gitHead = (& git rev-parse HEAD 2>&1 | Select-Object -Last 1) } catch { }
}
Write-Output ("GIT_HEAD: " + $gitHead)

# --- Directorio del paquete ------------------------------------------------------------
$distDir = Join-Path $ProjectRoot "dist"
$pkgDir = Join-Path $distDir "TukeVision"

Write-Step "LIMPIAR DIST ANTERIOR"
if (Test-Path -LiteralPath $distDir) {
    Remove-Item -LiteralPath $distDir -Recurse -Force -ErrorAction SilentlyContinue
}
New-Item -ItemType Directory -Path $pkgDir -Force | Out-Null

# --- Copiar archivos necesarios ----------------------------------------------------------
Write-Step "COPIAR ARCHIVOS"
$filesToCopy = @(
    "config",
    "docs",
    "install",
    "scripts",
    "src",
    "requirements.txt",
    "requirements.lock.txt",
    "README.md",
    "start_tukevision.ps1",
    "models\yolo11n.pt"
)

foreach ($item in $filesToCopy) {
    $src = Join-Path $ProjectRoot $item
    if (Test-Path -LiteralPath $src) {
        $dest = Join-Path $pkgDir $item
        $destParent = Split-Path -Parent $dest
        if ($destParent) { New-Item -ItemType Directory -Path $destParent -Force | Out-Null }
        Copy-Item -LiteralPath $src -Destination $dest -Recurse -Force
        Write-Output ("  copiado: " + $item)
    } else {
        Write-Output ("  ADVERTENCIA (no existe): " + $item)
    }
}

# --- Limpiar artefactos de Python del paquete -------------------------------------------
Write-Step "LIMPIAR ARTEFACTOS"
Get-ChildItem -LiteralPath $pkgDir -Recurse -Directory -Filter "__pycache__" -ErrorAction SilentlyContinue |
    Remove-Item -Recurse -Force -ErrorAction SilentlyContinue

# --- Crear carpetas de datos vacas ------------------------------------------------------
Write-Step "CREAR CARPETAS DE DATOS"
foreach ($dir in @("data\input", "data\output", "data\evidence", "data\temp", "logs")) {
    New-Item -ItemType Directory -Path (Join-Path $pkgDir $dir) -Force | Out-Null
}
New-Item -ItemType Directory -Path (Join-Path $pkgDir "models") -Force | Out-Null
foreach ($gitkeep in @("data\input\.gitkeep", "data\output\.gitkeep", "data\evidence\.gitkeep", "data\temp\.gitkeep", "logs\.gitkeep", "models\.gitkeep")) {
    $p = Join-Path $pkgDir $gitkeep
    if (-not (Test-Path -LiteralPath $p)) { Set-Content -LiteralPath $p -Value "" }
}
# models/yolo11n.pt ya se copi como artefacto requerido

# --- MANIFEST.json ------------------------------------------------------------------------
Write-Step "MANIFEST.JSON"
$modelPath = Join-Path $ProjectRoot "models\yolo11n.pt"
$modelSha = ""
if (Test-Path -LiteralPath $modelPath) {
    $modelSha = (Get-FileHash -LiteralPath $modelPath -Algorithm SHA256).Hash
}
$reqTxt = Join-Path $ProjectRoot "requirements.txt"
$reqSha = ""
if (Test-Path -LiteralPath $reqTxt) {
    $reqSha = (Get-FileHash -LiteralPath $reqTxt -Algorithm SHA256).Hash
}

$manifest = [ordered]@{
    package_version    = $PackageVersion
    build_date         = (Get-Date).ToString("yyyy-MM-dd")
    git_head           = $gitHead
    spec_certified_base = "cf876a9"
    python_required    = "3.12.x"
    model_filename     = "models/yolo11n.pt"
    model_sha256       = $modelSha
    requirements_sha256 = $reqSha
}
$manifestPath = Join-Path $pkgDir "MANIFEST.json"
$jsonUtf8 = $manifest | ConvertTo-Json
[System.IO.File]::WriteAllText($manifestPath, $jsonUtf8, (New-Object System.Text.UTF8Encoding $false))
Write-Output ("MANIFEST.json escrito en: " + $manifestPath)
Write-Output ("requirements_sha256: " + $reqSha)
Write-Output ("model_sha256: " + $modelSha)

# --- ZIP opcional -----------------------------------------------------------------------------
if (-not $NoZip) {
    Write-Step "ZIP"
    $zipPath = Join-Path $distDir "TukeVision-portable.zip"
    if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
    Compress-Archive -Path (Join-Path $pkgDir "*") -DestinationPath $zipPath -CompressionLevel Optimal
    Write-Output ("ZIP creado: " + $zipPath)
}

Write-Step "RESULTADO"
Write-Output ("PACKAGE_PATH: " + $pkgDir)
Write-Output "PACKAGE_STATUS: OK"
exit 0
