<#
.SYNOPSIS
    Inicia el emulador de Android virtual de Laboratorio HermesLab para Hermes Agent desde I:.
.DESCRIPTION
    Configura el entorno en I:\Proyectos\HermesAndroid\avd y arranca HermesLab con aceleracion AEHD/WHPX.
#>
[CmdletBinding()]
param(
    [switch]$Headless,
    [switch]$NoSnapshotLoad,
    [int]$TimeoutSeconds = 120,
    [int]$Port = 5556
)

$BASE_I = "I:\Proyectos\HermesAndroid"
$SDK_DIR = "C:\dev\android-sdk"
$EMU_EXE = "$SDK_DIR\emulator\emulator.exe"
$ADB_EXE = "$SDK_DIR\platform-tools\adb.exe"

# Variables de entorno dedicadas para I:
$env:ANDROID_AVD_HOME = "$BASE_I\avd"
$env:ANDROID_USER_HOME = "$BASE_I\.android"
$env:ANDROID_HOME = $SDK_DIR
$env:ANDROID_SDK_ROOT = $SDK_DIR

Write-Host "==========================================================" -ForegroundColor Magenta
Write-Host "   INICIANDO DISPOSITIVO DE LABORATORIO (HermesLab)" -ForegroundColor Magenta
Write-Host "   Ubicacion AVD: $env:ANDROID_AVD_HOME\HermesLab.avd" -ForegroundColor Yellow
Write-Host "   Puerto asignado: $Port (serial: emulator-$Port)" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Magenta

if (-not (Test-Path $EMU_EXE)) {
    Write-Error "No se encontro emulator.exe en $EMU_EXE"
    exit 1
}

# Construir argumentos de inicio
$emuArgs = @("-avd", "HermesLab", "-port", "$Port", "-gpu", "auto", "-accel", "auto")

if ($Headless) {
    Write-Host "[INFO] Modo Headless (sin ventana GUI) activado." -ForegroundColor Yellow
    $emuArgs += @("-no-window", "-no-audio", "-no-boot-anim")
}

if ($NoSnapshotLoad) {
    Write-Host "[INFO] Arranque en frio (sin cargar snapshot previo)." -ForegroundColor Yellow
    $emuArgs += @("-no-snapshot-load")
}

Write-Host "[1/3] Lanzando proceso del emulador HermesLab..." -ForegroundColor Green
$proc = Start-Process -FilePath $EMU_EXE -ArgumentList $emuArgs -PassThru -NoNewWindow

Write-Host "[2/3] Esperando que ADB reconozca el dispositivo emulator-$Port..." -ForegroundColor Green
Start-Sleep -Seconds 5

Write-Host "[3/3] Esperando que Android complete el arranque (sys.boot_completed = 1)..." -ForegroundColor Green
$startTime = Get-Date
$booted = $false
$serial = "emulator-$Port"

while ((Get-Date) - $startTime -lt (New-TimeSpan -Seconds $TimeoutSeconds)) {
    Start-Sleep -Seconds 2
    try {
        $bootProp = & $ADB_EXE -s $serial shell getprop sys.boot_completed 2>$null
        if ($bootProp.Trim() -eq "1") {
            $booted = $true
            break
        }
    } catch {
        # Continuando espera
    }
}

if ($booted) {
    Write-Host "==========================================================" -ForegroundColor Green
    Write-Host "   HERMES LAB LISTO Y OPERATIVO ($serial)" -ForegroundColor Green
    Write-Host "   Persistencia independiente: I:\Proyectos\HermesAndroid\avd\HermesLab.avd" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    & $ADB_EXE devices -l
    exit 0
} else {
    Write-Warning "HermesLab arranco pero sys.boot_completed tardo mas de $TimeoutSeconds s."
    & $ADB_EXE devices -l
    exit 2
}
