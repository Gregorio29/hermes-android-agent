"""
Registro y Descubrimiento de Dispositivos Android para Hermes.
Permite listar, identificar y seleccionar dispositivos físicos y virtuales de forma robusta.
"""

import os
import re
import subprocess
from typing import List, Dict, Optional, Tuple, Any
from models import DeviceInfo, DeviceType, DeviceState


class DeviceRegistry:
    """Gestiona el registro, descubrimiento y selección de dispositivos Android."""

    # Dispositivos formalmente conocidos por el sistema
    KNOWN_DEVICES = {
        "PHYSICAL_A71": {
            "name": "PHYSICAL_A71",
            "aliases": ["a71", "samsung", "samsung_a71", "physical_a71", "r58nb0lwkaj"],
            "type": DeviceType.PHYSICAL_A71,
            "target_model": "SM-A715F",
            "default_serial": "R58NB0LWKAJ",
        },
        "VIRTUAL_HERMES_PHONE": {
            "name": "HermesPhone",
            "aliases": ["hermesphone", "hermes_phone", "virtual_hermes_phone", "hermes", "emulator-5554"],
            "type": DeviceType.VIRTUAL_HERMES_PHONE,
            "avd_name": "HermesPhone",
            "avd_path": r"I:\Proyectos\HermesAndroid\avd\HermesPhone.avd",
        },
        "VIRTUAL_HERMES_LAB": {
            "name": "HermesLab",
            "aliases": ["hermeslab", "hermes_lab", "virtual_hermes_lab", "lab", "emulator-5556"],
            "type": DeviceType.VIRTUAL_HERMES_LAB,
            "avd_name": "HermesLab",
            "avd_path": r"I:\Proyectos\HermesAndroid\avd\HermesLab.avd",
        }
    }

    def __init__(self, sdk_dir: Optional[str] = None, avd_base_dir: Optional[str] = None):
        self.sdk_dir = sdk_dir or os.environ.get("ANDROID_HOME", os.environ.get("ANDROID_SDK_ROOT", r"C:\dev\android-sdk"))
        self.avd_base_dir = avd_base_dir or os.environ.get("HERMES_AVD_DIR", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "avd"))
        self.adb_path = os.path.join(self.sdk_dir, "platform-tools", "adb.exe" if os.name == "nt" else "adb")
        self.emulator_path = os.path.join(self.sdk_dir, "emulator", "emulator.exe" if os.name == "nt" else "emulator")
        self.selected_device: Optional[DeviceInfo] = None

    def _run_adb(self, args: List[str], serial: Optional[str] = None, timeout: int = 10) -> Tuple[int, str, str]:
        """Ejecuta un comando ADB con serial opcional."""
        cmd = [self.adb_path]
        if serial:
            cmd.extend(["-s", serial])
        cmd.extend(args)
        
        env = os.environ.copy()
        env["ANDROID_AVD_HOME"] = self.avd_base_dir
        env["ANDROID_USER_HOME"] = r"I:\Proyectos\HermesAndroid\.android"
        env["ANDROID_HOME"] = self.sdk_dir
        env["ANDROID_SDK_ROOT"] = self.sdk_dir

        try:
            p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, env=env)
            return p.returncode, p.stdout.strip(), p.stderr.strip()
        except subprocess.TimeoutExpired:
            return 124, "", "Comando ADB expirado por timeout"
        except Exception as e:
            return 1, "", str(e)

    def _get_device_property(self, serial: str, prop_name: str) -> str:
        """Consulta una propiedad del sistema Android via getprop."""
        code, out, _ = self._run_adb(["shell", "getprop", prop_name], serial=serial, timeout=5)
        if code == 0:
            return out.strip()
        return ""

    def list_connected_adb_devices(self) -> List[Dict[str, str]]:
        """Lista los dispositivos detectados activamente por el servidor ADB."""
        code, out, _ = self._run_adb(["devices", "-l"], timeout=5)
        if code != 0 or not out:
            return []

        devices = []
        lines = out.splitlines()
        for line in lines[1:]:  # Omitir header 'List of devices attached'
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) >= 2:
                serial = parts[0]
                status = parts[1]
                details = " ".join(parts[2:]) if len(parts) > 2 else ""
                devices.append({
                    "serial": serial,
                    "status": status,
                    "details": details
                })
        return devices

    def discover_devices(self) -> List[DeviceInfo]:
        """
        Escanea y unifica los dispositivos conectados vía ADB y los AVDs locales configurados.
        Identifica de forma estable a HermesPhone y al Samsung A71.
        """
        discovered: Dict[str, DeviceInfo] = {}

        # 1. Inspeccionar AVDs configurados en disco (I:\Proyectos\HermesAndroid\avd)
        if os.path.exists(self.avd_base_dir):
            for item in os.listdir(self.avd_base_dir):
                if item.endswith(".ini"):
                    avd_name = item[:-4]
                    avd_folder = os.path.join(self.avd_base_dir, f"{avd_name}.avd")
                    if avd_name.lower() == "hermesphone":
                        dev_type = DeviceType.VIRTUAL_HERMES_PHONE
                        default_serial = "emulator-5554"
                    elif avd_name.lower() == "hermeslab":
                        dev_type = DeviceType.VIRTUAL_HERMES_LAB
                        default_serial = "emulator-5556"
                    else:
                        dev_type = DeviceType.GENERIC_VIRTUAL
                        default_serial = None
                    discovered[avd_name] = DeviceInfo(
                        name=avd_name,
                        device_type=dev_type,
                        avd_name=avd_name,
                        avd_path=avd_folder,
                        serial=default_serial,
                        state=DeviceState.OFFLINE,
                        is_powered_on=False,
                        is_boot_completed=False,
                        model="Pixel 5 (Virtual)"
                    )

        # 2. Inspeccionar dispositivos conectados por ADB
        connected = self.list_connected_adb_devices()
        for c in connected:
            serial = c["serial"]
            status_str = c["status"]
            
            # Obtener propiedades para identificación certera
            is_emulator = serial.startswith("emulator-")
            avd_prop = ""
            model_prop = ""
            android_ver = ""
            sdk_ver_str = ""
            boot_completed = False

            if status_str == "device":
                avd_prop = self._get_device_property(serial, "ro.boot.qemu.avd_name") or self._get_device_property(serial, "ro.kernel.qemu.avd_name")
                model_prop = self._get_device_property(serial, "ro.product.model")
                android_ver = self._get_device_property(serial, "ro.build.version.release")
                sdk_ver_str = self._get_device_property(serial, "ro.build.version.sdk")
                boot_val = self._get_device_property(serial, "sys.boot_completed")
                boot_completed = (boot_val == "1")

            sdk_level = int(sdk_ver_str) if sdk_ver_str.isdigit() else None

            # Determinar tipo y nombre
            if is_emulator or avd_prop:
                if avd_prop:
                    avd_name = avd_prop
                elif serial == "emulator-5554":
                    avd_name = "HermesPhone"
                elif serial == "emulator-5556":
                    avd_name = "HermesLab"
                else:
                    avd_name = "GenericEmulator"

                if avd_name.lower() == "hermesphone":
                    dev_type = DeviceType.VIRTUAL_HERMES_PHONE
                elif avd_name.lower() == "hermeslab":
                    dev_type = DeviceType.VIRTUAL_HERMES_LAB
                else:
                    dev_type = DeviceType.GENERIC_VIRTUAL
                state = DeviceState.READY if boot_completed else (DeviceState.ONLINE if status_str == "device" else DeviceState.BOOTING)
                
                info = DeviceInfo(
                    name=avd_name,
                    device_type=dev_type,
                    serial=serial,
                    model=model_prop or "Google Pixel (Virtual)",
                    android_version=android_ver or "13",
                    sdk_level=sdk_level or 33,
                    state=state,
                    is_powered_on=True,
                    is_boot_completed=boot_completed,
                    avd_name=avd_name,
                    avd_path=os.path.join(self.avd_base_dir, f"{avd_name}.avd")
                )
                discovered[avd_name] = info

            else:
                # Dispositivo físico
                is_a71 = (serial == "R58NB0LWKAJ") or ("a71" in model_prop.lower()) or ("sm-a715" in model_prop.lower())
                dev_type = DeviceType.PHYSICAL_A71 if is_a71 else DeviceType.GENERIC_PHYSICAL
                dev_name = "PHYSICAL_A71" if is_a71 else f"PHYSICAL_{serial}"
                state = DeviceState.READY if (status_str == "device" and boot_completed) else (DeviceState.ONLINE if status_str == "device" else DeviceState.OFFLINE)
                
                info = DeviceInfo(
                    name=dev_name,
                    device_type=dev_type,
                    serial=serial,
                    model=model_prop or ("Samsung Galaxy A71" if is_a71 else "Android Device"),
                    brand="Samsung" if is_a71 else "Unknown",
                    android_version=android_ver,
                    sdk_level=sdk_level,
                    state=state,
                    is_powered_on=(status_str == "device"),
                    is_boot_completed=boot_completed
                )
                discovered[dev_name] = info

        # Asegurar que PHYSICAL_A71 esté listado aunque esté offline si no se detectó
        if "PHYSICAL_A71" not in discovered:
            discovered["PHYSICAL_A71"] = DeviceInfo(
                name="PHYSICAL_A71",
                device_type=DeviceType.PHYSICAL_A71,
                serial="R58NB0LWKAJ",
                model="Samsung Galaxy A71 (SM-A715F)",
                brand="Samsung",
                state=DeviceState.OFFLINE,
                is_powered_on=False,
                is_boot_completed=False
            )

        return list(discovered.values())

    def list_devices(self) -> List[Dict[str, Any]]:
        """Retorna la lista de dispositivos descubiertos en formato diccionario."""
        devices = self.discover_devices()
        return [d.to_dict() for d in devices]

    def select_device(self, identifier: str) -> Optional[DeviceInfo]:
        """
        Selecciona un dispositivo objetivo por nombre, alias, serial o tipo.
        Ejemplos: "HermesPhone", "VIRTUAL_HERMES_PHONE", "PHYSICAL_A71", "a71", "emulator-5554"
        """
        ident_lower = identifier.strip().lower()
        devices = self.discover_devices()

        # 1. Coincidencia exacta por nombre
        for d in devices:
            if d.name.lower() == ident_lower:
                self.selected_device = d
                return d

        # 2. Coincidencia por alias conocidos
        for key, conf in self.KNOWN_DEVICES.items():
            if ident_lower == key.lower() or ident_lower in conf.get("aliases", []):
                target_name = conf["name"]
                for d in devices:
                    if d.name.lower() == target_name.lower():
                        self.selected_device = d
                        return d

        # 3. Coincidencia por Serial ADB
        for d in devices:
            if d.serial and d.serial.lower() == ident_lower:
                self.selected_device = d
                return d

        # 4. Coincidencia parcial o por modelo
        for d in devices:
            if ident_lower in d.name.lower() or (d.model and ident_lower in d.model.lower()):
                self.selected_device = d
                return d

        return None

    def get_selected_device(self) -> Optional[DeviceInfo]:
        """Retorna el dispositivo actualmente seleccionado o selecciona HermesPhone por defecto."""
        if not self.selected_device:
            self.select_device("HermesPhone")
        return self.selected_device
