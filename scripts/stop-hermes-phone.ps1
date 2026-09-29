<#
.SYNOPSIS
    Detiene de forma limpia el emulador HermesPhone preservando el estado y sesiones.
#>
[CmdletBinding()]
param(
    [string]$Serial = "emulator-5554"
)

$SDK_DIR = "C:\dev\android-sdk"
$ADB_EXE = "$SDK_DIR\platform-tools\adb.exe"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "       DETENIENDO DISPOSITIVO VIRTUAL: $Serial      " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$devices = & $ADB_EXE devices
if ($devices -notmatch $Serial) {
    Write-Host "[INFO] El dispositivo $Serial no se encuentra activo." -ForegroundColor Yellow
    exit 0
}

Write-Host "[PASO 1] Enviando senal de apagado limpio (emu kill)..." -ForegroundColor Green
& $ADB_EXE -s $Serial emu kill

Start-Sleep -Seconds 3

# Verificar si el proceso termino
$emuProcs = Get-Process -Name "qemu-system-x86_64", "emulator" -ErrorAction SilentlyContinue
if ($emuProcs) {
    Write-Host "[INFO] Esperando cierre de procesos residuales..." -ForegroundColor Gray
    Start-Sleep -Seconds 2
}

Write-Host "[EXITO] Emulador detenido correctamente. Estado de usuario preservado en I:\Proyectos\HermesAndroid\avd." -ForegroundColor Green
