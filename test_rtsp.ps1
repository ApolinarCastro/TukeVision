<#>
.SYNOPSIS
    Launcher para test_rtsp_connection.py usando el entorno virtual del portable.

.DESCRIPTION
    Localiza automáticamente .venv\Scripts\python.exe y ejecuta
    scripts\test_rtsp_connection.py reenviando todos los argumentos.

    NO activa el entorno virtual permanentemente.
    NO contiene rutas absolutas.
    NO contiene credenciales.

.EXAMPLE
    .\test_rtsp.ps1 --host "rtsp://HOST:554/cam/realmonitor?channel=1&subtype=1" --username USER
    (La contraseña se solicita interactivamente)

.EXAMPLE
    .\test_rtsp.ps1 "rtsp://user:pass@host:554/path" --timeout 15 --max-frames 30
#>

param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$Args
)

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$VenvPython = Join-Path $ScriptDir ".venv\Scripts\python.exe"
$TestScript = Join-Path $ScriptDir "scripts\test_rtsp_connection.py"

if (-not (Test-Path -LiteralPath $VenvPython)) {
    Write-Error "No se encuentra el intérprete del entorno virtual: $VenvPython"
    exit 1
}

if (-not (Test-Path -LiteralPath $TestScript)) {
    Write-Error "No se encuentra el script de prueba: $TestScript"
    exit 1
}

& $VenvPython $TestScript @Args
exit $LASTEXITCODE
