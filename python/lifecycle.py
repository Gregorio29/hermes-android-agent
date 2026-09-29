"""
Gestor de Ciclo de Vida para HermesPhone y dispositivos virtuales.
Controla arranque con aceleración, sondeo de boot real, estado y apagado limpio.
"""

import os
import time
import subprocess
from typing import Dict, Any, Optional, Tuple
from models import DeviceInfo, DeviceState, DeviceType
from device_registry import DeviceRegistry


class LifecycleManager:
    """Gestiona el ciclo de vida de emuladores Android y dispositivos virtuales."""

    def __init__(self, registry: DeviceRegistry, sdk_dir: str = r"C:\dev\android-sdk", avd_base_dir: str = r"I:\Proyectos\HermesAndroid\avd"):
        self.registry = registry
        self.sdk_dir = sdk_dir
        self.avd_base_dir = avd_base_dir
        self.adb_path = os.path.join(sdk_dir, "platform-tools", "adb.exe")
        self.emulator_path = os.path.join(sdk_dir, "emulator", "emulator.exe")

    def _get_env(self) -> Dict[str, str]:
        """Prepara las variables de entorno de sesión apuntando a I:."""
        env = os.environ.copy()
        env["ANDROID_AVD_HOME"] = self.avd_base_dir
        env["ANDROID_USER_HOME"] = r"I:\Proyectos\HermesAndroid\.android"
        env["ANDROID_HOME"] = self.sdk_dir
        env["ANDROID_SDK_ROOT"] = self.sdk_dir
        return env

    def device_status(self, identifier: str = "HermesPhone") -> Dict[str, Any]:
        """
        Retorna el estado de ciclo de vida del dispositivo solicitado.
        Verifica proceso, conexión ADB y estado de boot del sistema Android.
        """
        device = self.registry.select_device(identifier)
        if not device:
            return {
                "name": identifier,
                "is_running": False,
                "is_boot_completed": False,
                "state": DeviceState.OFFLINE.value,
                "serial": None,
                "message": f"Dispositivo '{identifier}' no encontrado en el registro."
            }

        # Comprobar si el serial está online
        is_booted = False
        state = DeviceState.OFFLINE
        
        if device.serial:
            code, out, _ = self.registry._run_adb(["shell", "getprop", "sys.boot_completed"], serial=device.serial, timeout=5)
            if code == 0 and out.strip() == "1":
                is_booted = True
                state = DeviceState.READY
            elif code == 0:
                state = DeviceState.BOOTING
            else:
                state = DeviceState.ONLINE if device.is_powered_on else DeviceState.OFFLINE
        elif device.is_powered_on:
            state = DeviceState.BOOTING

        return {
            "name": device.name,
            "device_type": device.device_type.value,
            "serial": device.serial,
            "model": device.model,
            "is_running": (state in (DeviceState.READY, DeviceState.ONLINE, DeviceState.BOOTING)),
            "is_boot_completed": is_booted,
            "state": state.value,
            "avd_name": device.avd_name,
        }

    def wait_for_boot(self, identifier: str = "HermesPhone", timeout: int = 120, check_interval: int = 2) -> bool:
        """
        Espera activamente a que el dispositivo objetivo complete su arranque real.
        Comprueba: adb devices -> sys.boot_completed == "1" -> surfaceflinger / package manager.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Re-descubrir dispositivos
            device = self.registry.select_device(identifier)
            if device and device.serial:
                # Comprobar sys.boot_completed
                code, out, _ = self.registry._run_adb(["shell", "getprop", "sys.boot_completed"], serial=device.serial, timeout=5)
                if code == 0 and out.strip() == "1":
                    # Verificación secundaria: comprobar que responde el package manager o surfaceflinger
                    code_pm, out_pm, _ = self.registry._run_adb(["shell", "pm", "path", "android"], serial=device.serial, timeout=5)
                    if code_pm == 0 and "package:" in out_pm:
                        device.is_boot_completed = True
                        device.state = DeviceState.READY
                        return True
            time.sleep(check_interval)
        return False

    def start_device(self, identifier: str = "HermesPhone", headless: bool = False, cold_boot: bool = False, timeout: int = 120) -> Tuple[bool, str]:
        """
        Inicia el dispositivo virtual si no está corriendo y espera a que esté 100% operativo.
        """
        status = self.device_status(identifier)
        if status.get("is_boot_completed"):
            return True, f"Dispositivo '{identifier}' ya está iniciado y operativo (Serial: {status.get('serial')})."

        device = self.registry.select_device(identifier)
        if not device or device.device_type == DeviceType.PHYSICAL_A71:
            return False, f"No se puede iniciar automáticamente el dispositivo físico '{identifier}'. Conéctelo vía USB."

        avd_name = device.avd_name or "HermesPhone"

        # Construir argumentos de arranque del emulador
        cmd = [
            self.emulator_path,
            "-avd", avd_name,
            "-no-audio",
            "-no-boot-anim",
            "-gpu", "swiftshader_indirect",  # Renderizado estable
        ]
        
        if headless:
            cmd.append("-no-window")
        if cold_boot:
            cmd.append("-no-snapshot-load")

        env = self._get_env()

        try:
            # Iniciar proceso de emulador en segundo plano
            proc = subprocess.Popen(
                cmd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
            )
        except Exception as e:
            return False, f"Error al lanzar proceso de emulador: {e}"

        # Esperar a que complete el boot
        boot_ok = self.wait_for_boot(identifier, timeout=timeout)
        if boot_ok:
            updated_status = self.device_status(identifier)
            return True, f"Dispositivo '{identifier}' ({avd_name}) iniciado con éxito (PID: {proc.pid}, Serial: {updated_status.get('serial')})."
        else:
            return False, f"Dispositivo '{identifier}' ({avd_name}) inició el proceso (PID: {proc.pid}) pero no completó el arranque dentro de {timeout}s."

    def stop_device(self, identifier: str = "HermesPhone", force: bool = False) -> Tuple[bool, str]:
        """
        Detiene limpiamente el dispositivo virtual mediante 'emu kill' o termina el proceso.
        """
        device = self.registry.select_device(identifier)
        if not device or not device.serial:
            return True, f"Dispositivo '{identifier}' no está en ejecución."

        if device.device_type == DeviceType.PHYSICAL_A71:
            return False, "No se puede apagar un dispositivo físico mediante esta API."

        # Intentar apagado limpio via 'emu kill'
        code, out, err = self.registry._run_adb(["emu", "kill"], serial=device.serial, timeout=10)
        
        # Esperar a que se desconecte
        for _ in range(15):
            time.sleep(1)
            status = self.device_status(identifier)
            if not status.get("is_running"):
                return True, f"Dispositivo '{identifier}' detenido limpiamente."

        if force:
            # Si se exige forzar, matar procesos qemu/emulator asociados
            subprocess.run(["taskkill.exe", "/F", "/IM", "qemu-system-x86_64*"], capture_output=True)
            return True, f"Dispositivo '{identifier}' forzado a detenerse."

        return False, f"Dispositivo '{identifier}' no se detuvo tras enviar comando 'emu kill'."
