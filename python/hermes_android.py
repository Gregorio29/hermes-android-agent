"""
HERMES ANDROID AGENT — Controlador Unificado e Integración con Hermes.
Versión 2.0.0

Proporciona soporte completo para dispositivos físicos (Samsung A71) y virtuales (HermesPhone),
con registro dinámico, ciclo de vida con aceleración, herramientas Android avanzadas,
motor de misiones basado en estado real, control de seguridad operacional y almacenamiento en I:.
"""

import os
import sys
import json
import time
import argparse
from typing import List, Dict, Any, Optional, Tuple, Union, Callable

# Asegurar import de submódulos locales
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from models import (
    DeviceInfo, DeviceType, DeviceState, UIElement,
    Mission, MissionStep, StepResult, MissionReport
)
from security import SecurityPolicy, SecurityLevel
from device_registry import DeviceRegistry
from lifecycle import LifecycleManager
from android_controller import AndroidController
from mission_engine import MissionEngine


class HermesAndroidAgent:
    """Agente central de integración Android para Hermes."""

    KNOWN_ALIASES = {
        "PHYSICAL_A71": "R58NB0LWKAJ",
        "SAMSUNG_A71": "R58NB0LWKAJ",
        "A71": "R58NB0LWKAJ",
        "VIRTUAL_HERMES_PHONE": "emulator-5554",
        "HERMESPHONE": "emulator-5554",
        "HERMES_PHONE": "emulator-5554",
        "EMULATOR": "emulator-5554"
    }

    def __init__(
        self,
        sdk_dir: str = r"C:\dev\android-sdk",
        avd_base_dir: str = r"I:\Proyectos\HermesAndroid\avd",
        allow_sensitive: bool = False,
        allow_destructive: bool = False,
        device_target: Optional[str] = None
    ):
        self.sdk_dir = sdk_dir
        self.avd_base_dir = avd_base_dir
        self.adb_path = os.path.join(sdk_dir, "platform-tools", "adb.exe")
        self.emulator_path = os.path.join(sdk_dir, "emulator", "emulator.exe")

        # Inicialización de subsistemas modulares
        self.security_policy = SecurityPolicy(
            allow_sensitive=allow_sensitive,
            allow_destructive=allow_destructive
        )
        self.registry = DeviceRegistry(sdk_dir=sdk_dir, avd_base_dir=avd_base_dir)
        self.lifecycle = LifecycleManager(self.registry, sdk_dir=sdk_dir, avd_base_dir=avd_base_dir)
        self.controller = AndroidController(self.registry, self.security_policy)
        self.mission_engine = MissionEngine(
            registry=self.registry,
            lifecycle=self.lifecycle,
            controller=self.controller,
            security_policy=self.security_policy
        )

        # Seleccionar dispositivo inicial
        if device_target:
            self.select_device(device_target)
        else:
            self.select_device("HermesPhone")

    # -------------------------------------------------------------------------
    # Propiedades de compatibilidad
    # -------------------------------------------------------------------------

    @property
    def device_serial(self) -> Optional[str]:
        dev = self.registry.get_selected_device()
        return dev.serial if dev else None

    @device_serial.setter
    def device_serial(self, serial: Optional[str]):
        if serial:
            self.registry.select_device(serial)

    @property
    def active_device(self) -> Optional[DeviceInfo]:
        return self.registry.get_selected_device()

    def is_connected(self) -> bool:
        dev = self.active_device
        return bool(dev and dev.is_powered_on)

    # -------------------------------------------------------------------------
    # Registro y Selección de Dispositivos (FASE 2)
    # -------------------------------------------------------------------------

    def list_devices(self) -> List[Dict[str, Any]]:
        """Lista todos los dispositivos conectados o configurados."""
        return self.registry.list_devices()

    def select_device(self, identifier: str) -> bool:
        """Selecciona el dispositivo objetivo (ej: 'HermesPhone', 'PHYSICAL_A71', 'a71')."""
        dev = self.registry.select_device(identifier)
        return (dev is not None)

    # -------------------------------------------------------------------------
    # Ciclo de Vida de Dispositivos (FASE 3)
    # -------------------------------------------------------------------------

    def start_device(self, identifier: str = "HermesPhone", headless: bool = False, cold_boot: bool = False, timeout: int = 120) -> Tuple[bool, str]:
        """Arranca el dispositivo virtual y espera verificación real de boot."""
        return self.lifecycle.start_device(identifier, headless=headless, cold_boot=cold_boot, timeout=timeout)

    def start_emulator(self, avd_name: str = "HermesPhone", headless: bool = False, timeout_s: int = 120) -> bool:
        """Alias retrocompatible para start_device."""
        ok, _ = self.start_device(avd_name, headless=headless, timeout=timeout_s)
        return ok

    def wait_for_boot(self, identifier: str = "HermesPhone", timeout: int = 120) -> bool:
        """Espera a que el dispositivo objetivo complete su arranque real."""
        return self.lifecycle.wait_for_boot(identifier, timeout=timeout)

    def device_status(self, identifier: str = "HermesPhone") -> Dict[str, Any]:
        """Retorna el estado detallado de encendido y boot del dispositivo."""
        return self.lifecycle.device_status(identifier)

    def stop_device(self, identifier: str = "HermesPhone", force: bool = False) -> Tuple[bool, str]:
        """Detiene limpiamente el dispositivo virtual."""
        return self.lifecycle.stop_device(identifier, force=force)

    def stop_emulator(self, serial: str = "emulator-5554") -> bool:
        """Alias retrocompatible para stop_device."""
        ok, _ = self.stop_device(serial)
        return ok

    # -------------------------------------------------------------------------
    # Herramientas Android de Inspección e Interacción (FASE 4)
    # -------------------------------------------------------------------------

    def screenshot(self, output_path: Optional[str] = None) -> str:
        return self.controller.screenshot(output_path)

    def get_foreground_app(self) -> Dict[str, str]:
        return self.controller.get_foreground_app()

    def get_ui_tree(self, save_xml_path: Optional[str] = None) -> List[Dict[str, Any]]:
        elements, raw_xml = self.controller.get_ui_tree()
        if save_xml_path:
            with open(save_xml_path, "w", encoding="utf-8") as f:
                f.write(raw_xml)
        return [e.to_dict() for e in elements]

    def find_element(self, text: Optional[str] = None, resource_id: Optional[str] = None, content_desc: Optional[str] = None, class_name: Optional[str] = None, regex: bool = False) -> Optional[UIElement]:
        return self.controller.find_element(text=text, resource_id=resource_id, content_desc=content_desc, class_name=class_name, regex=regex)

    def find_elements(self, text: Optional[str] = None, resource_id: Optional[str] = None, content_desc: Optional[str] = None, class_name: Optional[str] = None, clickable_only: bool = False, regex: bool = False) -> List[UIElement]:
        return self.controller.find_elements(text=text, resource_id=resource_id, content_desc=content_desc, class_name=class_name, clickable_only=clickable_only, regex=regex)

    def tap(self, x: int, y: int) -> bool:
        return self.controller.tap(x, y)

    def tap_element(self, query: Union[UIElement, str, Dict[str, Any]]) -> bool:
        return self.controller.tap_element(query)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        return self.controller.swipe(x1, y1, x2, y2, duration_ms=duration_ms)

    def type(self, text: str) -> bool:
        return self.controller.type(text)

    def press(self, key: Union[str, int]) -> bool:
        return self.controller.press(key)

    def home(self) -> bool:
        return self.controller.home()

    def back(self) -> bool:
        return self.controller.back()

    def open_app(self, package_name: str, activity: Optional[str] = None) -> bool:
        return self.controller.open_app(package_name, activity=activity)

    def launch_app(self, package_name: str) -> bool:
        return self.controller.launch_app(package_name)

    def close_app(self, package_name: str) -> bool:
        return self.controller.close_app(package_name)

    def is_app_installed(self, package_name: str) -> bool:
        return self.controller.is_app_installed(package_name)

    def get_package_info(self, package_name: str) -> Dict[str, Any]:
        return self.controller.get_package_info(package_name)

    def install_app(self, apk_path: str) -> bool:
        return self.controller.install_app(apk_path)

    def wait_for(self, target: Union[str, Dict[str, Any]], timeout: float = 10.0) -> bool:
        return self.controller.wait_for(target, timeout=timeout)

    def verify(self, condition: Union[Dict[str, Any], Callable[['HermesAndroidAgent'], bool]]) -> Tuple[bool, str]:
        if callable(condition):
            try:
                res = condition(self)
                return res, "Verificación por función Callable exitosa" if res else "Verificación por Callable retornó False"
            except Exception as e:
                return False, f"Excepción en Callable de verificación: {e}"
        return self.controller.verify(condition)

    def get_device_info(self) -> Dict[str, Any]:
        dev = self.active_device
        return dev.to_dict() if dev else {}

    # -------------------------------------------------------------------------
    # Sistema de Misiones (FASE 5, 6, 7)
    # -------------------------------------------------------------------------

    def run_mission(self, mission: Union[Mission, Dict[str, Any], str]) -> MissionReport:
        """Ejecuta una misión completa registrando evidencia en I:."""
        return self.mission_engine.run_mission(mission)

    # -------------------------------------------------------------------------
    # Integración de Alto Nivel con Hermes (FASE 9)
    # -------------------------------------------------------------------------

    def execute_natural_instruction(self, instruction: str) -> Dict[str, Any]:
        """
        Traduce instrucciones de alto nivel emitidas por Hermes hacia misiones estructuradas.
        Ejemplo: "Usa HermesPhone y abre Settings"
        """
        inst_lower = instruction.lower().strip()
        device_name = "HermesPhone"
        
        # Detección de dispositivo
        if "a71" in inst_lower or "samsung" in inst_lower:
            device_name = "PHYSICAL_A71"
        elif "hermes" in inst_lower or "phone" in inst_lower:
            device_name = "HermesPhone"

        # Construcción de pasos según intención
        steps = []
        mission_name = f"Instruction_{int(time.time())}"

        if "settings" in inst_lower or "configuracion" in inst_lower or "ajustes" in inst_lower:
            mission_name = "Abrir_Settings"
            steps = [
                MissionStep(action="open_app", target="com.android.settings", step_id="STEP_01"),
                MissionStep(action="wait_for", target="com.android.settings", step_id="STEP_02"),
                MissionStep(action="screenshot", step_id="STEP_03"),
                MissionStep(
                    action="verify",
                    expected_state={"foreground_package": "com.android.settings"},
                    step_id="STEP_04"
                )
            ]
        elif "home" in inst_lower or "inicio" in inst_lower:
            mission_name = "Ir_A_Home"
            steps = [
                MissionStep(action="home", step_id="STEP_01"),
                MissionStep(action="screenshot", step_id="STEP_02"),
            ]
        elif "screenshot" in inst_lower or "captura" in inst_lower:
            mission_name = "Captura_Pantalla"
            steps = [
                MissionStep(action="screenshot", step_id="STEP_01")
            ]
        else:
            # Instrucción genérica: tomar captura e inspeccionar
            mission_name = "Inspeccion_Generica"
            steps = [
                MissionStep(action="screenshot", step_id="STEP_01"),
                MissionStep(action="verify", expected_state={"is_boot_completed": True}, step_id="STEP_02")
            ]

        mission = Mission(
            name=mission_name,
            device=device_name,
            description=instruction,
            steps=steps
        )

        report = self.run_mission(mission)
        return report.to_dict()


# -----------------------------------------------------------------------------
# Interfaz de Línea de Comandos (CLI)
# -----------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Hermes Android Agent CLI v2.0")
    parser.add_argument("--device", "-d", help="Dispositivo objetivo (HermesPhone, HermesLab, PHYSICAL_A71)")
    subparsers = parser.add_subparsers(dest="command", help="Comandos disponibles")

    # devices
    subparsers.add_parser("devices", help="Listar dispositivos detectados")

    # select
    select_p = subparsers.add_parser("select", help="Seleccionar dispositivo activo")
    select_p.add_argument("device", help="Nombre o alias del dispositivo")

    # start
    start_p = subparsers.add_parser("start", help="Iniciar emulador")
    start_p.add_argument("device", nargs="?", default="HermesPhone", help="Nombre del AVD")
    start_p.add_argument("--headless", action="store_true", help="Modo sin ventana")
    start_p.add_argument("--cold", action="store_true", help="Arranque en frío")

    # stop
    stop_p = subparsers.add_parser("stop", help="Detener emulador")
    stop_p.add_argument("device", nargs="?", default="HermesPhone", help="Nombre del AVD")

    # status
    status_p = subparsers.add_parser("status", help="Consultar estado del dispositivo")
    status_p.add_argument("device", nargs="?", default="HermesPhone", help="Nombre del AVD")

    # screenshot
    shot_p = subparsers.add_parser("screenshot", help="Tomar captura de pantalla")
    shot_p.add_argument("--out", "-o", help="Ruta de salida")

    # debug
    debug_p = subparsers.add_parser("debug", help="Diagnosticar aplicación (Black Box vs Debuggable)")
    debug_p.add_argument("package", help="Nombre del paquete (ej: com.hermes.debugtarget)")

    # watch
    watch_p = subparsers.add_parser("watch", help="Monitorear aplicación en vivo para detectar fallos")
    watch_p.add_argument("package", help="Nombre del paquete")
    watch_p.add_argument("--duration", "-d", type=float, default=10.0, help="Duración del monitoreo en segundos")

    # logcat
    logcat_p = subparsers.add_parser("logcat", help="Ver registros de logcat recientes")
    logcat_p.add_argument("--lines", "-n", type=int, default=50, help="Número de líneas a mostrar")
    logcat_p.add_argument("--package", "-p", help="Filtrar por nombre de paquete")

    # dumpsys
    dumpsys_p = subparsers.add_parser("dumpsys", help="Consultar servicio del sistema con dumpsys")
    dumpsys_p.add_argument("service", nargs="?", default="activity", help="Nombre del servicio (activity, package, meminfo, etc.)")

    # mission
    mission_p = subparsers.add_parser("mission", help="Ejecutar archivo de misión JSON")
    mission_p.add_argument("file", help="Ruta al archivo mission.json")

    # run-instruction
    inst_p = subparsers.add_parser("instruction", help="Ejecutar instrucción en lenguaje natural")
    inst_p.add_argument("text", help="Texto de la instrucción")

    args = parser.parse_args()
    agent = HermesAndroidAgent(device_target=args.device)

    if args.command == "devices" or not args.command:
        devs = agent.list_devices()
        print("\n=== DISPOSITIVOS REGISTRADOS EN HERMES ANDROID ===")
        for d in devs:
            status_icon = "🟢 LISTO" if d["is_boot_completed"] else ("🟡 INICIANDO" if d["is_powered_on"] else "🔴 OFFLINE")
            print(f"[{status_icon}] {d['name']:<20} | Tipo: {d['device_type']:<20} | Serial: {str(d['serial']):<15} | Modelo: {d.get('model', 'N/A')}")
        print()

    elif args.command == "select":
        ok = agent.select_device(args.device)
        if ok:
            print(f"Dispositivo seleccionado: {agent.active_device.name} (Serial: {agent.active_device.serial})")
        else:
            print(f"No se pudo seleccionar: {args.device}")

    elif args.command == "start":
        print(f"Iniciando dispositivo {args.device}...")
        ok, msg = agent.start_device(args.device, headless=args.headless, cold_boot=args.cold)
        print(msg)

    elif args.command == "stop":
        print(f"Deteniendo dispositivo {args.device}...")
        ok, msg = agent.stop_device(args.device)
        print(msg)

    elif args.command == "status":
        st = agent.device_status(args.device)
        print(json.dumps(st, indent=2, ensure_ascii=False))

    elif args.command == "screenshot":
        out = agent.screenshot(args.out)
        print(f"Screenshot guardado en: {out}")

    elif args.command == "debug":
        diag = agent.controller.debug_app(args.package)
        print(json.dumps(diag, indent=2, ensure_ascii=False))

    elif args.command == "watch":
        print(f"Iniciando monitoreo de {args.package} durante {args.duration}s...")
        res = agent.controller.watch_app(args.package, duration=args.duration)
        print(json.dumps(res, indent=2, ensure_ascii=False))

    elif args.command == "logcat":
        logs = agent.controller.logcat(package=args.package, lines=args.lines)
        print(logs)

    elif args.command == "dumpsys":
        dump = agent.controller.dumpsys(args.service)
        print(dump)

    elif args.command == "mission":
        report = agent.run_mission(args.file)
        print(f"Misión finalizada. Éxito: {report.success}. Evidencia en: {report.evidence_dir}")

    elif args.command == "instruction":
        res = agent.execute_natural_instruction(args.text)
        print(json.dumps(res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
