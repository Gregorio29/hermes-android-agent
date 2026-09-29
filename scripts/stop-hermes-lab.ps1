<#
.SYNOPSIS
    Detiene de manera limpia o forzada el emulador HermesLab.
#>
[CmdletBinding()]
param(
    [switch]$Force,
    [int]$Port = 5556
)

$SDK_DIR = "C:\dev\android-sdk"
$ADB_EXE = "$SDK_DIR\platform-tools\adb.exe"
$serial = "emulator-$Port"

Write-Host "[INFO] Deteniendo HermesLab ($serial)..." -ForegroundColor Yellow

if (-not $Force) {
    try {
        & $ADB_EXE -s $serial emu kill 2>$null
        Start-Sleep -Seconds 3
    } catch {}
}

# Comprobar procesos residuales de qemu si se solicito forzado
if ($Force) {
    Get-Process qemu-system* -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*HermesLab*" } | Stop-Process -Force
}

Write-Host "[OK] HermesLab detenido." -ForegroundColor Green
