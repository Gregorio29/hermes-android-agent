"""
Controlador de Herramientas Android para Hermes.
Implementa interacción ADB, inspección de UIAutomator, captura y verificación.
"""

import os
import re
import time
import subprocess
import xml.etree.ElementTree as ET
from typing import List, Dict, Any, Optional, Tuple, Union

from models import DeviceInfo, UIElement, DeviceState, DeviceType
from device_registry import DeviceRegistry
from security import SecurityPolicy, SecurityLevel
from debug_controller import DebugController


class AndroidController:
    """Proporciona herramientas de interacción, inspección y verificación con dispositivos Android."""

    KEY_MAP = {
        "HOME": "3",
        "BACK": "4",
        "CALL": "5",
        "ENDCALL": "6",
        "UP": "19",
        "DOWN": "20",
        "LEFT": "21",
        "RIGHT": "22",
        "CENTER": "23",
        "VOLUME_UP": "24",
        "VOLUME_DOWN": "25",
        "POWER": "26",
        "CAMERA": "27",
        "CLEAR": "28",
        "ENTER": "66",
        "DELETE": "67",
        "TAB": "61",
        "SPACE": "62",
        "MENU": "82",
        "APP_SWITCH": "187",
    }

    def __init__(self, registry: DeviceRegistry, security_policy: Optional[SecurityPolicy] = None):
        self.registry = registry
        self.security_policy = security_policy or SecurityPolicy()
        self.debug = DebugController(self)
        self.default_screenshots_dir = r"I:\Proyectos\HermesAndroid\screenshots"
        self.default_logs_dir = r"I:\Proyectos\HermesAndroid\logs"
        os.makedirs(self.default_screenshots_dir, exist_ok=True)
        os.makedirs(self.default_logs_dir, exist_ok=True)

    @property
    def current_device(self) -> Optional[DeviceInfo]:
        """Retorna el dispositivo actualmente seleccionado."""
        return self.registry.get_selected_device()

    @property
    def serial(self) -> str:
        """Retorna el serial del dispositivo seleccionado."""
        dev = self.current_device
        if dev and dev.serial:
            return dev.serial
        raise RuntimeError("No hay un dispositivo activo con serial ADB disponible.")

    def run_adb(self, args: List[str], timeout: int = 15) -> Tuple[int, str, str]:
        """Ejecuta un comando ADB sobre el dispositivo actualmente seleccionado."""
        return self.registry._run_adb(args, serial=self.serial, timeout=timeout)

    def run_shell(self, command: str, timeout: int = 15) -> Tuple[int, str, str]:
        """Ejecuta un comando en la shell del dispositivo seleccionado."""
        return self.run_adb(["shell", command], timeout=timeout)

    # -------------------------------------------------------------------------
    # Herramientas de Inspección y Lectura (SAFE)
    # -------------------------------------------------------------------------

    def screenshot(self, output_path: Optional[str] = None) -> str:
        """
        Captura la pantalla del dispositivo y la almacena localmente.
        Retorna la ruta absoluta del archivo PNG generado.
        """
        if not output_path:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.default_screenshots_dir, f"screenshot_{timestamp}.png")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        remote_path = "/sdcard/hermes_screencap.png"

        code, out, err = self.run_shell(f"screencap -p {remote_path}")
        if code != 0:
            raise RuntimeError(f"Fallo al capturar pantalla en dispositivo: {err}")

        # Descargar archivo a ruta local
        code_pull, _, err_pull = self.run_adb(["pull", remote_path, output_path])
        if code_pull != 0 or not os.path.exists(output_path):
            raise RuntimeError(f"Fallo al transferir captura localmente: {err_pull}")

        # Limpiar archivo temporal en el dispositivo
        self.run_shell(f"rm -f {remote_path}")
        return output_path

    def get_foreground_app(self) -> Dict[str, str]:
        """
        Obtiene el paquete y actividad de la aplicación en primer plano actual.
        Retorna {"package": str, "activity": str, "raw": str}.
        """
        code, out, _ = self.run_shell("dumpsys window | grep -E 'mCurrentFocus|mFocusedApp'")
        if code != 0 or not out:
            # Fallback con dumpsys activity
            code, out, _ = self.run_shell("dumpsys activity activities | grep -E 'mResumedActivity|topResumedActivity'")

        result = {"package": "unknown", "activity": "unknown", "raw": out.strip()}
        
        # Parsear con expresiones regulares comunes de dumpsys
        # Ej: u0 com.android.settings/.Settings
        match = re.search(r"([a-zA-Z0-9_\.]+)/([a-zA-Z0-9_\.]+)", out)
        if match:
            result["package"] = match.group(1)
            result["activity"] = match.group(2)
        return result

    def get_ui_tree(self) -> Tuple[List[UIElement], str]:
        """
        Ejecuta UIAutomator dump en el dispositivo, descarga y parsea el XML de la jerarquía UI.
        Retorna (lista_de_nodos_UIElement, xml_crudo_como_str).
        """
        remote_xml = "/sdcard/window_dump.xml"
        
        # Eliminar archivo previo si existe
        self.run_shell(f"rm -f {remote_xml}")
        
        code, out, err = self.run_shell(f"uiautomator dump {remote_xml}")
        if code != 0:
            raise RuntimeError(f"Error al ejecutar uiautomator dump: {err or out}")

        code_cat, raw_xml, err_cat = self.run_shell(f"cat {remote_xml}")
        if code_cat != 0 or not raw_xml:
            raise RuntimeError(f"Error al leer XML de UIAutomator: {err_cat}")

        elements: List[UIElement] = []
        try:
            root = ET.fromstring(raw_xml)
            for elem in root.iter("node"):
                attrib = elem.attrib
                bounds_str = attrib.get("bounds", "[0,0][0,0]")
                
                # Parsear bounds: "[left,top][right,bottom]"
                coords = (0, 0, 0, 0)
                cx, cy = 0, 0
                b_match = re.match(r"\[(\d+),(\d+)\]\[(\d+),(\d+)\]", bounds_str)
                if b_match:
                    left, top, right, bottom = map(int, b_match.groups())
                    coords = (left, top, right, bottom)
                    cx = (left + right) // 2
                    cy = (top + bottom) // 2

                ui_node = UIElement(
                    index=attrib.get("index", ""),
                    text=attrib.get("text", ""),
                    resource_id=attrib.get("resource-id", ""),
                    class_name=attrib.get("class", ""),
                    package=attrib.get("package", ""),
                    content_desc=attrib.get("content-desc", ""),
                    checkable=(attrib.get("checkable") == "true"),
                    checked=(attrib.get("checked") == "true"),
                    clickable=(attrib.get("clickable") == "true"),
                    enabled=(attrib.get("enabled") == "true"),
                    focusable=(attrib.get("focusable") == "true"),
                    focused=(attrib.get("focused") == "true"),
                    scrollable=(attrib.get("scrollable") == "true"),
                    long_clickable=(attrib.get("long-clickable") == "true"),
                    password=(attrib.get("password") == "true"),
                    selected=(attrib.get("selected") == "true"),
                    bounds=bounds_str,
                    bounds_coords=coords,
                    center_x=cx,
                    center_y=cy
                )
                elements.append(ui_node)
        except Exception as e:
            raise RuntimeError(f"Error al parsear estructura XML de UI: {e}")

        return elements, raw_xml

    def find_elements(
        self,
        text: Optional[str] = None,
        resource_id: Optional[str] = None,
        content_desc: Optional[str] = None,
        class_name: Optional[str] = None,
        clickable_only: bool = False,
        regex: bool = False
    ) -> List[UIElement]:
        """
        Busca elementos en la jerarquía UI actual según múltiples criterios.
        """
        elements, _ = self.get_ui_tree()
        matches: List[UIElement] = []

        for el in elements:
            if clickable_only and not el.clickable:
                continue

            if text is not None:
                if regex:
                    if not re.search(text, el.text, re.IGNORECASE):
                        continue
                else:
                    if text.lower() not in el.text.lower():
                        continue

            if resource_id is not None:
                if regex:
                    if not re.search(resource_id, el.resource_id, re.IGNORECASE):
                        continue
                else:
                    if resource_id.lower() not in el.resource_id.lower():
                        continue

            if content_desc is not None:
                if regex:
                    if not re.search(content_desc, el.content_desc, re.IGNORECASE):
                        continue
                else:
                    if content_desc.lower() not in el.content_desc.lower():
                        continue

            if class_name is not None:
                if class_name.lower() not in el.class_name.lower():
                    continue

            matches.append(el)

        return matches

    def find_element(
        self,
        text: Optional[str] = None,
        resource_id: Optional[str] = None,
        content_desc: Optional[str] = None,
        class_name: Optional[str] = None,
        clickable_only: bool = False,
        regex: bool = False
    ) -> Optional[UIElement]:
        """Retorna el primer elemento que coincida con los criterios dados."""
        matches = self.find_elements(
            text=text,
            resource_id=resource_id,
            content_desc=content_desc,
            class_name=class_name,
            clickable_only=clickable_only,
            regex=regex
        )
        return matches[0] if matches else None

    # -------------------------------------------------------------------------
    # Herramientas de Interacción (REVERSIBLE)
    # -------------------------------------------------------------------------

    def tap(self, x: int, y: int) -> bool:
        """Realiza un toque táctil en las coordenadas (x, y) de la pantalla."""
        code, _, _ = self.run_shell(f"input tap {x} {y}")
        return (code == 0)

    def tap_element(self, element_or_query: Union[UIElement, str, Dict[str, Any]]) -> bool:
        """
        Localiza un elemento por texto/query o toma un UIElement y toca sus coordenadas centrales.
        """
        target_el: Optional[UIElement] = None

        if isinstance(element_or_query, UIElement):
            target_el = element_or_query
        elif isinstance(element_or_query, str):
            # Intentar encontrar por texto, luego por content-desc, luego por resource-id
            target_el = self.find_element(text=element_or_query)
            if not target_el:
                target_el = self.find_element(content_desc=element_or_query)
            if not target_el:
                target_el = self.find_element(resource_id=element_or_query)
        elif isinstance(element_or_query, dict):
            target_el = self.find_element(
                text=element_or_query.get("text"),
                resource_id=element_or_query.get("resource_id"),
                content_desc=element_or_query.get("content_desc"),
                class_name=element_or_query.get("class_name")
            )

        if not target_el:
            return False

        return self.tap(target_el.center_x, target_el.center_y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """Realiza un gesto de deslizamiento entre dos puntos en la pantalla."""
        code, _, _ = self.run_shell(f"input swipe {x1} {y1} {x2} {y2} {duration_ms}")
        return (code == 0)

    def type(self, text: str) -> bool:
        """Escribe una cadena de texto en el campo enfocado."""
        escaped = text.replace(" ", "%s").replace("&", "\\&").replace("<", "\\<").replace(">", "\\>")
        code, _, _ = self.run_shell(f"input text \"{escaped}\"")
        return (code == 0)

    def press(self, key: Union[str, int]) -> bool:
        """Envía una pulsación de tecla física o virtual (ej: 'BACK', 'HOME', 4, 3)."""
        key_str = str(key).upper()
        keycode = self.KEY_MAP.get(key_str, str(key))
        code, _, _ = self.run_shell(f"input keyevent {keycode}")
        return (code == 0)

    def home(self) -> bool:
        """Presiona el botón HOME."""
        return self.press("HOME")

    def back(self) -> bool:
        """Presiona el botón BACK."""
        return self.press("BACK")

    def open_app(self, package_name: str, activity: Optional[str] = None) -> bool:
        """Abre o lanza una aplicación en primer plano."""
        if activity:
            component = f"{package_name}/{activity}" if not activity.startswith(package_name) else f"{package_name}/{activity}"
            code, _, _ = self.run_shell(f"am start -n {component}")
        else:
            # Lanzamiento automático mediante monkey launch intent
            code, _, _ = self.run_shell(f"monkey -p {package_name} -c android.intent.category.LAUNCHER 1")
        return (code == 0)

    def launch_app(self, package_name: str) -> bool:
        """Alias para open_app."""
        return self.open_app(package_name)

    def close_app(self, package_name: str) -> bool:
        """Detiene forzosamente una aplicación."""
        code, _, _ = self.run_shell(f"am force-stop {package_name}")
        return (code == 0)

    # -------------------------------------------------------------------------
    # Herramientas de Diagnóstico y Debugging (SAFE / READ_ONLY)
    # -------------------------------------------------------------------------

    def logcat(self, package: Optional[str] = None, filter_specs: Optional[List[str]] = None, lines: int = 100, buffer_name: Optional[str] = None, clear_first: bool = False) -> str:
        """Vuelca logcat no bloqueante."""
        return self.debug.logcat(package=package, filter_specs=filter_specs, lines=lines, buffer_name=buffer_name, clear_first=clear_first)

    def clear_logcat(self, buffer_name: Optional[str] = None) -> bool:
        """Limpia los búferes de logcat."""
        return self.debug.clear_logcat(buffer_name=buffer_name)

    def dumpsys(self, service: str = "activity", args: Optional[List[str]] = None) -> str:
        """Consulta servicios dumpsys."""
        return self.debug.dumpsys(service=service, args=args)

    def get_processes(self) -> List[Dict[str, Any]]:
        """Lista procesos en ejecución."""
        return self.debug.get_processes()

    def get_app_uid(self, package_name: str) -> Optional[int]:
        """Obtiene el UID de la aplicación."""
        return self.debug.get_app_uid(package_name)

    def is_app_debuggable(self, package_name: str) -> bool:
        """Verifica si la app fue compilada con debuggable=true."""
        return self.debug.is_app_debuggable(package_name)

    def get_app_version(self, package_name: str) -> Dict[str, Any]:
        """Obtiene la versión de la aplicación."""
        return self.debug.get_app_version(package_name)

    def capture_bugreport(self, output_path: Optional[str] = None) -> str:
        """Genera un bugreport oficial del dispositivo."""
        return self.debug.capture_bugreport(output_path)

    def debug_app(self, package_name: str) -> Dict[str, Any]:
        """Diagnóstico unificado de aplicación (Black Box vs Debuggable)."""
        return self.debug.debug_app(package_name)

    def watch_app(self, package_name: str, duration: float = 10.0, check_interval: float = 1.0, evidence_dir: Optional[str] = None) -> Dict[str, Any]:
        """Monitorea una aplicación para detectar anomalías o fallos."""
        return self.debug.watch_app(package_name, duration=duration, check_interval=check_interval, evidence_dir=evidence_dir)

    # -------------------------------------------------------------------------
    # Gestión de Paquetes
    # -------------------------------------------------------------------------

    def is_app_installed(self, package_name: str) -> bool:
        """Comprueba si un paquete está instalado en el dispositivo."""
        code, out, _ = self.run_shell(f"pm list packages {package_name}")
        return (code == 0 and f"package:{package_name}" in out)

    def get_package_info(self, package_name: str) -> Dict[str, Any]:
        """Obtiene información detallada del paquete instalado (versión, UID, debuggable, permisos)."""
        return self.debug.get_package_info(package_name)

    def install_app(self, apk_path: str, replace_existing: bool = True) -> bool:
        """Instala un paquete APK en el dispositivo."""
        if not os.path.exists(apk_path):
            raise FileNotFoundError(f"Archivo APK no encontrado: {apk_path}")
        flags = ["install"]
        if replace_existing:
            flags.append("-r")
        flags.append(apk_path)
        code, out, _ = self.run_adb(flags, timeout=60)
        return (code == 0 and "Success" in out)

    # -------------------------------------------------------------------------
    # Espera y Verificación Basada en Estado Real (Truth Gating)
    # -------------------------------------------------------------------------

    def wait_for(self, target: Union[str, Dict[str, Any]], timeout: float = 10.0, check_interval: float = 1.0) -> bool:
        """
        Espera a que un texto, elemento o paquete aparezca en pantalla.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            if isinstance(target, str):
                # Comprobar si coincide con paquete en primer plano
                fg = self.get_foreground_app()
                if target in fg.get("package", ""):
                    return True
                # Comprobar si existe en árbol de UI
                el = self.find_element(text=target) or self.find_element(content_desc=target)
                if el:
                    return True
            elif isinstance(target, dict):
                el = self.find_element(
                    text=target.get("text"),
                    resource_id=target.get("resource_id"),
                    content_desc=target.get("content_desc"),
                    class_name=target.get("class_name")
                )
                if el:
                    return True
            time.sleep(check_interval)
        return False

    def verify(self, expected_state: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Verifica formalmente el estado real del dispositivo contra condiciones esperadas.
        Condiciones soportadas en expected_state:
          - "foreground_package": nombre del paquete esperado en primer plano
          - "ui_contains_text": texto que debe existir en el árbol UI
          - "ui_not_contains_text": texto que NO debe existir en el árbol UI
          - "element_visible": diccionario con criterios de búsqueda de elemento
          - "is_boot_completed": booleano
        """
        # 1. Comprobar boot
        if "is_boot_completed" in expected_state:
            expected_boot = expected_state["is_boot_completed"]
            code, out, _ = self.run_shell("getprop sys.boot_completed")
            actual_boot = (out.strip() == "1")
            if actual_boot != expected_boot:
                return False, f"Boot verification falló: esperado={expected_boot}, actual={actual_boot}"

        # 2. Comprobar Foreground Package
        if "foreground_package" in expected_state:
            expected_pkg = expected_state["foreground_package"]
            fg = self.get_foreground_app()
            if expected_pkg.lower() not in fg["package"].lower():
                return False, f"Foreground package incorrecto: esperado='{expected_pkg}', actual='{fg['package']}'"

        # 3. Comprobar Texto en UI
        if "ui_contains_text" in expected_state:
            expected_text = expected_state["ui_contains_text"]
            el = self.find_element(text=expected_text) or self.find_element(content_desc=expected_text)
            if not el:
                return False, f"Texto esperado '{expected_text}' no encontrado en la UI."

        # 4. Comprobar Ausencia de Texto en UI
        if "ui_not_contains_text" in expected_state:
            forbidden_text = expected_state["ui_not_contains_text"]
            el = self.find_element(text=forbidden_text) or self.find_element(content_desc=forbidden_text)
            if el:
                return False, f"Texto prohibido '{forbidden_text}' presente en la UI."

        # 5. Comprobar Elemento visible
        if "element_visible" in expected_state:
            crit = expected_state["element_visible"]
            if isinstance(crit, dict):
                el = self.find_element(
                    text=crit.get("text"),
                    resource_id=crit.get("resource_id"),
                    content_desc=crit.get("content_desc"),
                    class_name=crit.get("class_name")
                )
                if not el:
                    return False, f"Elemento esperado no visible: {crit}"

        return True, "Verificación de estado real exitosa."

    # -------------------------------------------------------------------------
    # Delegaciones de Laboratorio y MITM (HermesLab)
    # -------------------------------------------------------------------------

    def lab_status(self) -> Dict[str, Any]:
        """Consulta el estado integral del laboratorio en el dispositivo actual."""
        return self.debug.lab_status()

    def root_status(self) -> Dict[str, Any]:
        """Consulta el estado y privilegios de Root."""
        return self.debug.root_status()

    def magisk_status(self) -> Dict[str, Any]:
        """Consulta el estado del entorno Magisk."""
        return self.debug.magisk_status()

    def reqable_status(self) -> Dict[str, Any]:
        """Consulta el estado de Reqable, certificados y captura."""
        return self.debug.reqable_status()

    def reqable_start_capture(self) -> bool:
        """Inicia la captura de tráfico HTTP/HTTPS con Reqable."""
        return self.debug.reqable_start_capture()

    def reqable_stop_capture(self) -> bool:
        """Detiene la captura de tráfico en Reqable."""
        return self.debug.reqable_stop_capture()

    def reqable_export_module(self, dest_path: Optional[str] = None) -> Optional[str]:
        """Exporta el módulo Magisk de CA a I:."""
        return self.debug.reqable_export_module(dest_path)

