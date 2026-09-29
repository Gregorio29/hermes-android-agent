<#
.SYNOPSIS
    Verifica el estado, conectividad ADB y subsistemas del emulador HermesPhone.
#>
[CmdletBinding()]
param(
    [string]$Serial = "emulator-5554"
)

$SDK_DIR = "C:\dev\android-sdk"
$ADB_EXE = "$SDK_DIR\platform-tools\adb.exe"

Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "       VERIFICACION TECNICA: $Serial               " -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan

$devices = & $ADB_EXE devices -l
Write-Host "[1. DISPOSITIVOS DETECTADOS]" -ForegroundColor Green
Write-Host $devices

if ($devices -notmatch $Serial) {
    Write-Host "[ADVERTENCIA] $Serial no esta en la lista de dispositivos activos." -ForegroundColor Yellow
    Write-Host "Ejecuta launch-hermes-phone.ps1 para arrancarlo." -ForegroundColor Gray
    exit 1
}

Write-Host "`n[2. PROPIEDADES DEL SISTEMA VIRTUAL]" -ForegroundColor Green
$model = & $ADB_EXE -s $Serial shell getprop ro.product.model
$brand = & $ADB_EXE -s $Serial shell getprop ro.product.brand
$androidVer = & $ADB_EXE -s $Serial shell getprop ro.build.version.release
$sdk = & $ADB_EXE -s $Serial shell getprop ro.build.version.sdk
$boot = & $ADB_EXE -s $Serial shell getprop sys.boot_completed
$wmSize = & $ADB_EXE -s $Serial shell wm size
$wmDensity = & $ADB_EXE -s $Serial shell wm density

Write-Host "  * Fabricante:    $brand"
Write-Host "  * Modelo:        $model"
Write-Host "  * Android:       $androidVer (API $sdk)"
Write-Host "  * Boot Status:   $boot"
Write-Host "  * $wmSize"
Write-Host "  * $wmDensity"

Write-Host "`n[3. PRUEBA DE SUBSISTEMAS AUTOMATIZABLES]" -ForegroundColor Green
# Prueba de screencap
$testImg = "I:\Proyectos\HermesAndroid\screenshots\test_verify.png"
& $ADB_EXE -s $Serial exec-out screencap -p > $testImg
if (Test-Path $testImg) {
    $imgSize = (Get-Item $testImg).Length
    Write-Host "  * Screencap:     OK ($imgSize bytes generados en I:\Proyectos\HermesAndroid\screenshots)" -ForegroundColor Green
    Remove-Item $testImg -Force -ErrorAction SilentlyContinue
} else {
    Write-Host "  * Screencap:     FALLO" -ForegroundColor Red
}

# Prueba de UIAutomator
$uiDump = & $ADB_EXE -s $Serial shell uiautomator dump /sdcard/window_dump.xml
if ($uiDump -match "dumped to") {
    Write-Host "  * UIAutomator:   OK ($uiDump)" -ForegroundColor Green
} else {
    Write-Host "  * UIAutomator:   RESPONDIÓ ($uiDump)" -ForegroundColor Yellow
}

Write-Host "`n[DIAGNÓSTICO COMPLETO] Dispositivo verificado y listo para Hermes." -ForegroundColor Cyan
