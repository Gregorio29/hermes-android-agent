<#
.SYNOPSIS
    Inicia el emulador de Android virtual HermesPhone para Hermes Agent desde I:.
.DESCRIPTION
    Configura el entorno en I:\Proyectos\HermesAndroid\avd y arranca HermesPhone con aceleracion.
#>
[CmdletBinding()]
param(
    [switch]$Headless,
    [switch]$NoSnapshotLoad,
    [int]$TimeoutSeconds = 90
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

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host "   INICIANDO DISPOSITIVO VIRTUAL HERMES (HermesPhone)" -ForegroundColor Cyan
Write-Host "   Ubicacion AVD: $env:ANDROID_AVD_HOME\HermesPhone.avd" -ForegroundColor Yellow
Write-Host "==========================================================" -ForegroundColor Cyan

if (-not (Test-Path $EMU_EXE)) {
    Write-Error "No se encontro emulator.exe en $EMU_EXE"
    exit 1
}

# Construir argumentos de inicio
$emuArgs = @("-avd", "HermesPhone", "-gpu", "auto", "-accel", "auto")

if ($Headless) {
    Write-Host "[INFO] Modo Headless (sin ventana GUI) activado." -ForegroundColor Yellow
    $emuArgs += @("-no-window", "-no-audio", "-no-boot-anim")
}

if ($NoSnapshotLoad) {
    Write-Host "[INFO] Arranque en frio (sin cargar snapshot previo)." -ForegroundColor Yellow
    $emuArgs += @("-no-snapshot-load")
}

Write-Host "[1/3] Lanzando proceso del emulador..." -ForegroundColor Green
$proc = Start-Process -FilePath $EMU_EXE -ArgumentList $emuArgs -PassThru -NoNewWindow

Write-Host "[2/3] Esperando que ADB reconozca el dispositivo..." -ForegroundColor Green
& $ADB_EXE wait-for-device

Write-Host "[3/3] Esperando que Android complete el arranque (sys.boot_completed = 1)..." -ForegroundColor Green
$startTime = Get-Date
$booted = $false

while ((Get-Date) - $startTime -lt (New-TimeSpan -Seconds $TimeoutSeconds)) {
    Start-Sleep -Seconds 2
    try {
        $bootProp = & $ADB_EXE -s emulator-5554 shell getprop sys.boot_completed 2>$null
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
    Write-Host "   HERMES PHONE LISTO Y OPERATIVO (emulator-5554)" -ForegroundColor Green
    Write-Host "   Persistencia: ACTIVADA en I:\Proyectos\HermesAndroid\avd" -ForegroundColor Green
    Write-Host "==========================================================" -ForegroundColor Green
    & $ADB_EXE devices -l
    exit 0
} else {
    Write-Warning "El emulador arranco pero sys.boot_completed tardo mas de $TimeoutSeconds s."
    & $ADB_EXE devices -l
    exit 2
}
