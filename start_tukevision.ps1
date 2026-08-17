# start_tukevision.ps1 - Inicia la interfaz operativa local de TukeVision
#
# Verifica el .venv, lo usa directamente (sin requerir activacin manual)
# y ejecuta scripts/run_interface.py.
#
# Uso:
#     powershell.exe -ExecutionPolicy Bypass -File start_tukevision.ps1
#
# Acceso directo sugerido:
#     powershell.exe -ExecutionPolicy Bypass -File "C:\ruta\a\TukeVision\start_tukevision.ps1"

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path

$venvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
$runScript = Join-Path $ProjectRoot "scripts\run_interface.py"
$multiScript = Join-Path $ProjectRoot "scripts\run_multicamera.py"
$Mode = "Single"
if ($args.Count -eq 2 -and $args[0] -eq "-Mode") { $Mode = $args[1] }

if (-not (Test-Path -LiteralPath $venvPython)) {
    Write-Output "ERROR: entorno virtual no encontrado (.venv)"
    Write-Output "Ejecute primero: powershell.exe -ExecutionPolicy Bypass -File install\install.ps1"
    exit 1
}

if (-not (Test-Path -LiteralPath $runScript)) {
    Write-Output "ERROR: scripts\run_interface.py no encontrado"
    exit 1
}

if ($Mode -ieq "Multicamera") {
    if (-not (Test-Path -LiteralPath $multiScript)) {
        Write-Output "ERROR: scripts\run_multicamera.py no encontrado"
        exit 1
    }
    Write-Output "Iniciando TukeVision modo multicámara..."
    & $venvPython $multiScript
    exit $LASTEXITCODE
}

Write-Output "Iniciando TukeVision..."
& $venvPython $runScript
exit $LASTEXITCODE
