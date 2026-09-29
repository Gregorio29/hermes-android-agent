<#
.SYNOPSIS
    Configura las variables de entorno de sesion para Hermes Android en la unidad I:.
.DESCRIPTION
    Establece ANDROID_AVD_HOME y ANDROID_USER_HOME apuntando a I:\Proyectos\HermesAndroid\
    y anade las herramientas del SDK al PATH para la sesion actual.
#>

$BASE_I = "I:\Proyectos\HermesAndroid"
$SDK_DIR = "C:\dev\android-sdk"

# Rutas dedicadas en I:
$env:ANDROID_AVD_HOME = "$BASE_I\avd"
$env:ANDROID_USER_HOME = "$BASE_I\.android"
$env:ANDROID_HOME = $SDK_DIR
$env:ANDROID_SDK_ROOT = $SDK_DIR

# Asegurar directorios
if (-not (Test-Path $env:ANDROID_AVD_HOME)) { New-Item -ItemType Directory -Path $env:ANDROID_AVD_HOME -Force | Out-Null }
if (-not (Test-Path $env:ANDROID_USER_HOME)) { New-Item -ItemType Directory -Path $env:ANDROID_USER_HOME -Force | Out-Null }

# Agregar herramientas al PATH de sesion si no estan presentes
$pathsToAdd = @(
    "$SDK_DIR\platform-tools",
    "$SDK_DIR\emulator",
    "$SDK_DIR\cmdline-tools\latest\bin"
)

foreach ($p in $pathsToAdd) {
    if ((Test-Path $p) -and ($env:PATH -notlike "*$p*")) {
        $env:PATH = "$p;$env:PATH"
    }
}

Write-Host "[OK] Entorno Hermes Android configurado en I:" -ForegroundColor Green
Write-Host "     ANDROID_AVD_HOME  : $env:ANDROID_AVD_HOME" -ForegroundColor Cyan
Write-Host "     ANDROID_USER_HOME : $env:ANDROID_USER_HOME" -ForegroundColor Cyan
Write-Host "     ANDROID_HOME      : $env:ANDROID_HOME" -ForegroundColor Cyan
