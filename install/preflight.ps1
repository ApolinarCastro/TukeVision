# preflight.ps1 - Verificacion previa de requisitos para TukeVision
#
# Solo inspecciona el sistema. No modifica nada.
#
# Uso:
#     powershell.exe -ExecutionPolicy Bypass -File install\preflight.ps1
#
# Salida:
#     OS, ARCH, PYTHON, RAM_GB, FREE_DISK_GB, WRITE_ACCESS,
#     MODEL_PRESENT, REQUIREMENTS_PRESENT, FINAL_STATUS
#
# Veredictos:
#     READY   - todos los requisitos criticos cumplidos
#     WARNING - hay advertencias no bloqueantes
#     BLOCKED - hay un requisito crtico incumplido

$ErrorActionPreference = "Stop"
$ScriptPath = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptPath

function Write-Field([string]$Name, [string]$Value) {
    Write-Output ("{0}: {1}" -f $Name, $Value)
}

$blocking = @()
$warnings = @()

# --- Windows 64 bits -------------------------------------------------------
$osCaption = "UNKNOWN"
$osArch = "UNKNOWN"
try {
    $os = Get-CimInstance -ClassName Win32_OperatingSystem
    $osCaption = "$($os.Caption) (build $($os.BuildNumber))"
    if ($os.OSArchitecture -match "64") { $osArch = "x64" }
    else { $osArch = $os.OSArchitecture; $blocking += "Windows no es de 64 bits" }
} catch {
    $blocking += "No se pudo consultar el sistema operativo"
}
Write-Field "OS" $osCaption
Write-Field "ARCH" $osArch

# --- PowerShell -------------------------------------------------------------
$psMajor = $PSVersionTable.PSVersion.Major
$psMinor = $PSVersionTable.PSVersion.Minor
Write-Field "POWERSHELL" "$psMajor.$psMinor"
if ($psMajor -lt 5) { $blocking += "PowerShell 5+ requerido" }

# --- Python -----------------------------------------------------------------
$pyVersion = "NOT_FOUND"
$pyLauncher = $false
$pythonCmd = $null

# Intentar el launcher py -3.12 primero
if (Get-Command py -ErrorAction SilentlyContinue) {
    try {
        $v = & py -3.12 -c "import sys; print(sys.version.split()[0])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $v -match "3\.12\.\d+") {
            $pyVersion = $v
            $pyLauncher = $true
        }
    } catch { }
}

# Si no, intentar python (solo si es 3.12.x)
if ($pyVersion -eq "NOT_FOUND" -and (Get-Command python -ErrorAction SilentlyContinue)) {
    try {
        $v = & python -c "import sys; print(sys.version.split()[0])" 2>$null
        if ($LASTEXITCODE -eq 0 -and $v -match "3\.12\.\d+") {
            $pyVersion = $v
            $pyLauncher = $false
        }
    } catch { }
}

Write-Field "PYTHON" $pyVersion
if ($pyVersion -eq "NOT_FOUND") {
    $blocking += "Python 3.12.x no disponible"
} elseif ($pyVersion -notmatch "3\.12\.\d+") {
    $blocking += "Se requiere Python 3.12.x (encontrado: $pyVersion)"
}

# --- RAM total ----------------------------------------------------------------
$ramGb = 0.0
try {
    $cs = Get-CimInstance -ClassName Win32_ComputerSystem
    $ramGb = [math]::Round($cs.TotalPhysicalMemory / 1GB, 1)
} catch { }
Write-Field "RAM_GB" "$ramGb"
if ($ramGb -gt 0 -and $ramGb -lt 4) { $warnings += "RAM menor a 4 GB (minimo experimental)" }

# --- Espacio libre -------------------------------------------------------------
$freeDiskGb = 0.0
try {
    $drive = Get-PSDrive -Name (Split-Path -Qualifier $ProjectRoot).TrimEnd(":")
    $freeDiskGb = [math]::Round($drive.Free / 1GB, 1)
} catch { }
Write-Field "FREE_DISK_GB" "$freeDiskGb"
if ($freeDiskGb -gt 0 -and $freeDiskGb -lt 5) { $blocking += "Espacio libre menor a 5 GB" }

# --- Acceso de escritura al directorio -------------------------------------------
$writeAccess = "NO"
try {
    $probe = Join-Path $ProjectRoot ".preflight_write_probe"
    Set-Content -LiteralPath $probe -Value "probe" -ErrorAction Stop
    Remove-Item -LiteralPath $probe -Force -ErrorAction Stop
    $writeAccess = "YES"
} catch {
    $blocking += "Sin acceso de escritura al directorio"
}
Write-Field "WRITE_ACCESS" $writeAccess

# --- Git opcional ---------------------------------------------------------------
$gitVersion = "NOT_FOUND"
if (Get-Command git -ErrorAction SilentlyContinue) {
    try { $gitVersion = & git --version 2>$null } catch { }
}
Write-Field "GIT" $gitVersion

# --- Modelo presente -------------------------------------------------------------
$modelPath = Join-Path $ProjectRoot "models\yolo11n.pt"
$modelPresent = "NO"
if (Test-Path -LiteralPath $modelPath) { $modelPresent = "YES" }
else { $blocking += "Modelo models/yolo11n.pt no encontrado" }
Write-Field "MODEL_PRESENT" $modelPresent

# --- Requirements presentes --------------------------------------------------------
$reqTxt = Join-Path $ProjectRoot "requirements.txt"
$reqLock = Join-Path $ProjectRoot "requirements.lock.txt"
$reqPresent = "NO"
if ((Test-Path -LiteralPath $reqTxt) -and (Test-Path -LiteralPath $reqLock)) { $reqPresent = "YES" }
else { $blocking += "requirements.txt o requirements.lock.txt no encontrados" }
Write-Field "REQUIREMENTS_PRESENT" $reqPresent

# --- Veredicto ----------------------------------------------------------------------
$final = "READY"
if ($blocking.Count -gt 0) { $final = "BLOCKED" }
elseif ($warnings.Count -gt 0) { $final = "WARNING" }
Write-Field "FINAL_STATUS" $final

if ($blocking.Count -gt 0) {
    Write-Output ""
    Write-Output "PROBLEMAS BLOQUEANTES:"
    foreach ($b in $blocking) { Write-Output ("  - " + $b) }
}
if ($warnings.Count -gt 0) {
    Write-Output ""
    Write-Output "ADVERTENCIAS:"
    foreach ($w in $warnings) { Write-Output ("  - " + $w) }
}

exit 0
