<#
.SYNOPSIS
    Verifica el estado, persistencia y aislamiento de HermesLab.
#>
$BASE_I = "I:\Proyectos\HermesAndroid"
$SDK_DIR = "C:\dev\android-sdk"
$ADB_EXE = "$SDK_DIR\platform-tools\adb.exe"

Write-Host "=== VERIFICACION DE HERMES LAB ===" -ForegroundColor Magenta
$avdPath = "$BASE_I\avd\HermesLab.avd"
$iniPath = "$BASE_I\avd\HermesLab.ini"

if (Test-Path $iniPath) {
    Write-Host "[OK] HermesLab.ini existe." -ForegroundColor Green
} else {
    Write-Error "[FAIL] Falta HermesLab.ini"
}

if (Test-Path $avdPath) {
    Write-Host "[OK] Directorio HermesLab.avd existe." -ForegroundColor Green
} else {
    Write-Error "[FAIL] Falta directorio HermesLab.avd"
}

# Verificacion de dispositivos ADB
& $ADB_EXE devices -l
