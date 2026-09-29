# DOCUMENTACIÓN TÉCNICA OFICIAL: ANDROID EMULATOR & SDK TOOLS

**Fecha de consulta:** 26 de septiembre de 2026  
**Fuentes primarias:** Android Developers (Google Developer Portal)

---

## 1. Android Emulator & Aceleración de Hardware
* **Referencia Oficial:** [Android Emulator Command Line Reference](https://developer.android.com/studio/run/emulator-commandline)
* **Aceleración en Windows (WHPX / Hyper-V):** [Configure Hardware Acceleration on Windows](https://developer.android.com/studio/run/emulator-acceleration#vm-windows)
  * *Mecanismo:* Windows Hypervisor Platform (WHPX) permite la virtualización anidada y acelerada de imágenes x86_64 coexistiendo de forma nativa con Hyper-V, WSL2 y Windows Sandbox.
  * *Flags recomendados:* `-accel on -gpu auto -no-boot-anim -no-snapshot-load` (o con snapshot para arranque instantáneo).
  * *Verificación:* `emulator -accel-check`.

---

## 2. Gestión de Componentes del SDK y AVDs
* **sdkmanager:** [sdkmanager CLI Reference](https://developer.android.com/tools/sdkmanager)
  * *Comando:* `sdkmanager --install "emulator" "system-images;android-33;google_apis;x86_64"`
  * *Aceptación automática de licencias:* `echo y | sdkmanager --licenses`
* **avdmanager:** [avdmanager CLI Reference](https://developer.android.com/tools/avdmanager)
  * *Creación:* `avdmanager create avd -n HermesPhone -k "system-images;android-33;google_apis;x86_64" --device "pixel_5"`
  * *Ubicación del AVD:* `%USERPROFILE%\.android\avd\HermesPhone.avd\`

---

## 3. Arquitectura de Automatización: ADB & UIAutomator
* **Android Debug Bridge (ADB):** [ADB Overview and Protocol](https://developer.android.com/tools/adb)
  * *Comprobación de arranque:* `adb wait-for-device && adb shell getprop sys.boot_completed` (debe retornar `1`).
  * *Control de dispositivo explícito:* `adb -s emulator-5554 <command>`.
  * *Detención limpia del emulador:* `adb -s emulator-5554 emu kill`.
* **UIAutomator:** [Testing UI with UIAutomator](https://developer.android.com/training/testing/other-components/ui-automator)
  * *Extracción de árbol visual:* `adb shell uiautomator dump /sdcard/window_dump.xml`.
  * *Interacciones de pantalla:* `adb shell input tap X Y`, `adb shell input text "string"`, `adb shell input swipe X1 Y1 X2 Y2 [ms]`, `adb shell input keyevent <KEY>`.

---

## 4. Persistencia y Snapshots
* **Persistencia de disco:** La partición `userdata.img` (y `userdata-qemu.img`) almacena todas las apps instaladas, configuraciones, cuentas y bases de datos locales entre reinicios.
* **Quick Boot / Snapshots:** [Working with Snapshots](https://developer.android.com/studio/run/emulator-snapshots)
  * *Configuración:* `fastboot.forceColdBoot = no` en `config.ini` permite reanudar el estado exacto de memoria y procesos en segundos.
