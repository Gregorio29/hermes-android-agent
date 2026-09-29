"""
Módulo de Diagnóstico, Inspección y Debugging para Android en Hermes Agent.
Proporciona capacidades avanzadas no-root (Black Box y Debuggable) y soporte de monitoreo en vivo.
"""

import os
import re
import time
import subprocess
from typing import List, Dict, Any, Optional, Tuple, Union


class DebugController:
    """Controlador especializado en diagnóstico, profiling y depuración de aplicaciones Android."""

    def __init__(self, controller):
        """
        Recibe una instancia de AndroidController para ejecutar comandos ADB/Shell.
        """
        self.controller = controller
        self.debug_output_dir = r"I:\Proyectos\HermesAndroid\debug"
        os.makedirs(self.debug_output_dir, exist_ok=True)

    def logcat(
        self,
        package: Optional[str] = None,
        filter_specs: Optional[List[str]] = None,
        lines: int = 100,
        buffer_name: Optional[str] = None,
        clear_first: bool = False
    ) -> str:
        """
        Vuelca registros de logcat de manera no bloqueante (-d).
        Soporta filtrado por paquete (resolviendo PID) o por especificaciones de tags.
        """
        if clear_first:
            self.clear_logcat(buffer_name)

        cmd = ["logcat", "-d"]
        if buffer_name:
            cmd.extend(["-b", buffer_name])
        
        if lines > 0:
            cmd.extend(["-t", str(lines)])

        if package:
            # Buscar PID actual del paquete
            pid = self.get_app_pid(package)
            if pid:
                cmd.extend(["--pid", str(pid)])

        if filter_specs:
            cmd.extend(filter_specs)

        code, out, err = self.controller.run_adb(cmd, timeout=20)
        return out if code == 0 else f"Error al obtener logcat: {err}"

    def clear_logcat(self, buffer_name: Optional[str] = None) -> bool:
        """Limpia los búferes circulares de logcat."""
        cmd = ["logcat", "-c"]
        if buffer_name:
            cmd.extend(["-b", buffer_name])
        code, _, _ = self.controller.run_adb(cmd, timeout=10)
        return (code == 0)

    def dumpsys(self, service: str = "activity", args: Optional[List[str]] = None) -> str:
        """
        Interroga los servicios del sistema Android mediante dumpsys (sin root).
        Ejemplos de servicio: activity, window, package, meminfo, battery, cpuinfo.
        """
        cmd = f"dumpsys {service}"
        if args:
            cmd += " " + " ".join(args)
        code, out, err = self.controller.run_shell(cmd, timeout=20)
        return out if code == 0 else f"Error en dumpsys {service}: {err}"

    def get_processes(self) -> List[Dict[str, Any]]:
        """
        Lista los procesos activos en el sistema mediante 'ps -A' o 'ps -ef'.
        Retorna lista de diccionarios con {pid, ppid, user, name, rss, vsz}.
        """
        code, out, _ = self.controller.run_shell("ps -A -o USER,PID,PPID,VSZ,RSS,NAME")
        if code != 0 or not out:
            # Fallback a ps estándar
            code, out, _ = self.controller.run_shell("ps")

        processes: List[Dict[str, Any]] = []
        lines = out.strip().splitlines()
        if not lines:
            return processes

        # Parsear salida
        header = lines[0].split()
        for line in lines[1:]:
            parts = line.split()
            if len(parts) >= 6:
                try:
                    processes.append({
                        "user": parts[0],
                        "pid": int(parts[1]),
                        "ppid": int(parts[2]),
                        "vsz": parts[3],
                        "rss": parts[4],
                        "name": parts[-1]
                    })
                except (ValueError, IndexError):
                    continue
            elif len(parts) >= 4:
                processes.append({
                    "user": parts[0],
                    "pid": int(parts[1]) if parts[1].isdigit() else 0,
                    "name": parts[-1]
                })

        return processes

    def get_app_pid(self, package_name: str) -> Optional[int]:
        """Obtiene el Process ID (PID) de una aplicación activa."""
        code, out, _ = self.controller.run_shell(f"pidof {package_name}")
        if code == 0 and out.strip():
            parts = out.strip().split()
            if parts and parts[0].isdigit():
                return int(parts[0])

        # Búsqueda alternativa en lista de procesos
        for proc in self.get_processes():
            if proc.get("name") == package_name:
                return proc.get("pid")
        return None

    def get_package_info(self, package_name: str) -> Dict[str, Any]:
        """
        Obtiene información técnica completa de un paquete instalado en el dispositivo.
        """
        raw_dump = self.dumpsys("package", [package_name])
        if f"Unable to find package: {package_name}" in raw_dump or not raw_dump.strip():
            return {
                "installed": False,
                "package": package_name,
                "error": "Paquete no encontrado en el sistema."
            }

        # Extraer campos clave con expresiones regulares
        version_name_m = re.search(r"versionName=([^\s]+)", raw_dump)
        version_code_m = re.search(r"versionCode=([0-9]+)", raw_dump)
        uid_m = re.search(r"userId=([0-9]+)|uid=([0-9]+)", raw_dump)
        target_sdk_m = re.search(r"targetSdk=([0-9]+)", raw_dump)
        min_sdk_m = re.search(r"minSdk=([0-9]+)", raw_dump)
        data_dir_m = re.search(r"dataDir=([^\s]+)", raw_dump)
        code_path_m = re.search(r"codePath=([^\s]+)", raw_dump)
        
        # Flags de depuración
        # Android dumpsys incluye flags: [ DEBUGGABLE HAS_CODE ALLOW_BACKUP ... ]
        flags_m = re.search(r"flags=\[\s*([^\]]+)\s*\]", raw_dump)
        flags_list = flags_m.group(1).split() if flags_m else []
        is_debuggable = "DEBUGGABLE" in flags_list or "DEBUGGABLE" in raw_dump

        # Extraer permisos solicitados y concedidos
        permissions = self.get_app_permissions(package_name, raw_dump=raw_dump)

        uid_val = None
        if uid_m:
            uid_val = int(uid_m.group(1) or uid_m.group(2))

        return {
            "installed": True,
            "package": package_name,
            "version_name": version_name_m.group(1) if version_name_m else "unknown",
            "version_code": int(version_code_m.group(1)) if version_code_m else None,
            "uid": uid_val,
            "target_sdk": int(target_sdk_m.group(1)) if target_sdk_m else None,
            "min_sdk": int(min_sdk_m.group(1)) if min_sdk_m else None,
            "data_dir": data_dir_m.group(1) if data_dir_m else f"/data/data/{package_name}",
            "code_path": code_path_m.group(1) if code_path_m else None,
            "is_debuggable": is_debuggable,
            "flags": flags_list,
            "permissions": permissions,
        }

    def get_app_permissions(self, package_name: str, raw_dump: Optional[str] = None) -> Dict[str, List[str]]:
        """Extrae la lista de permisos solicitados y concedidos de la app."""
        if not raw_dump:
            raw_dump = self.dumpsys("package", [package_name])

        requested: List[str] = []
        granted: List[str] = []

        req_section = False
        grant_section = False

        for line in raw_dump.splitlines():
            line_str = line.strip()
            if "requested permissions:" in line.lower():
                req_section = True
                grant_section = False
                continue
            elif "install permissions:" in line.lower() or "runtime permissions:" in line.lower():
                grant_section = True
                req_section = False
                continue
            elif line_str.endswith(":") and not ("permission" in line_str.lower()):
                req_section = False
                grant_section = False

            if req_section and line_str and not line_str.startswith("User"):
                perm = line_str.split(":")[0].strip()
                if perm and perm not in requested:
                    requested.append(perm)
            elif grant_section and "granted=true" in line_str:
                perm_match = re.search(r"([a-zA-Z0-9_\.]+): granted=true", line_str)
                if perm_match:
                    granted.append(perm_match.group(1))

        return {"requested": requested, "granted": granted}

    def get_app_uid(self, package_name: str) -> Optional[int]:
        """Retorna el UID asignado por Android al paquete."""
        info = self.get_package_info(package_name)
        return info.get("uid")

    def is_app_debuggable(self, package_name: str) -> bool:
        """
        Determina si una aplicación fue compilada con android:debuggable='true'.
        Si es debuggable, soporta JDWP attach, run-as y acceso directo a su sandbox.
        """
        info = self.get_package_info(package_name)
        return info.get("is_debuggable", False)

    def get_app_version(self, package_name: str) -> Dict[str, Any]:
        """Retorna versión textual (versionName) y numérica (versionCode)."""
        info = self.get_package_info(package_name)
        return {
            "version_name": info.get("version_name"),
            "version_code": info.get("version_code")
        }

    def capture_bugreport(self, output_path: Optional[str] = None) -> str:
        """
        Genera y descarga un bugreport formal de Android via ADB.
        """
        if not output_path:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            output_path = os.path.join(self.debug_output_dir, f"bugreport_{timestamp}.zip")

        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        code, _, err = self.controller.run_adb(["bugreport", output_path], timeout=180)
        if code != 0:
            raise RuntimeError(f"Error al generar bugreport: {err}")
        return output_path

    def get_recent_errors(self, package_name: Optional[str] = None, lines: int = 200) -> List[Dict[str, str]]:
        """
        Busca excepciones no controladas, ANRs o crashes en logcat.
        """
        raw_logs = self.logcat(package=None, lines=lines)
        errors = []
        
        # Patrones comunes de error crítico en Android
        crash_patterns = [
            r"FATAL EXCEPTION:\s*(.*)",
            r"AndroidRuntime:\s*FATAL EXCEPTION:\s*(.*)",
            r"Process:\s*([a-zA-Z0-9_\.]+),\s*PID:\s*(\d+)",
            r"ANR in\s*([a-zA-Z0-9_\.]+)",
            r"Caused by:\s*([a-zA-Z0-9_\.]+Exception:.*)"
        ]

        current_error: Optional[Dict[str, str]] = None
        for line in raw_logs.splitlines():
            if package_name and package_name not in line and "AndroidRuntime" not in line and "FATAL" not in line:
                continue

            for pattern in crash_patterns:
                match = re.search(pattern, line)
                if match:
                    if "FATAL EXCEPTION" in line or "ANR in" in line:
                        if current_error:
                            errors.append(current_error)
                        current_error = {
                            "type": "CRASH" if "FATAL" in line else "ANR",
                            "header": line.strip(),
                            "details": []
                        }
                    elif current_error:
                        current_error["details"].append(line.strip())

        if current_error:
            errors.append(current_error)

        return errors

    # -------------------------------------------------------------------------
    # FASE 8: Diagnóstico Unificado (android.debug_app)
    # -------------------------------------------------------------------------

    def debug_app(self, package_name: str) -> Dict[str, Any]:
        """
        Diagnóstico unificado de una aplicación Android:
        1. Verifica instalación.
        2. Obtiene metadatos de paquete.
        3. Verifica si es debuggable.
        4. Identifica PID y procesos activos.
        5. Captura logs recientes.
        6. Obtiene actividad y ventana en primer plano.
        7. Evalúa soporte de JDWP / Debugger Attach.
        8. Retorna dict estructurado con categorización Black Box vs Debuggable.
        """
        pkg_info = self.get_package_info(package_name)
        if not pkg_info.get("installed"):
            return {
                "package": package_name,
                "status": "NOT_INSTALLED",
                "diagnosis": "La aplicación no está instalada en el dispositivo.",
                "black_box": {"available": False},
                "debugger_attach": "NO"
            }

        pid = self.get_app_pid(package_name)
        fg = self.controller.get_foreground_app()
        is_in_foreground = (fg.get("package") == package_name)
        is_debuggable = pkg_info.get("is_debuggable", False)

        # Verificar si aparece en JDWP (depuración activa ART)
        code_jdwp, out_jdwp, _ = self.controller.run_adb(["jdwp"])
        jdwp_pids = out_jdwp.split() if code_jdwp == 0 else []
        jdwp_available = (str(pid) in jdwp_pids) if pid else False

        # Logs recientes asociados al paquete o runtime
        recent_errors = self.get_recent_errors(package_name=package_name, lines=150)
        recent_logs = self.logcat(package=package_name, lines=40)

        diagnosis = {
            "package": package_name,
            "version": f"{pkg_info.get('version_name')} ({pkg_info.get('version_code')})",
            "uid": pkg_info.get("uid"),
            "pid": pid,
            "status": "RUNNING" if pid else "STOPPED",
            "is_foreground": is_in_foreground,
            "current_activity": fg.get("activity") if is_in_foreground else None,
            "debugger_attach": "YES (JDWP Active)" if jdwp_available else ("CAPABLE (App is debuggable)" if is_debuggable else "NO (Production/Non-Debuggable)"),
            "inspection_mode": "DEBUGGABLE (Full Sandbox & JDWP)" if is_debuggable else "BLACK_BOX (UIAutomator, Dumpsys & Observable Logs)",
            "black_box_capabilities": {
                "ui_inspection": True,
                "screenshot": True,
                "dumpsys": True,
                "observable_logs": True
            },
            "debuggable_capabilities": {
                "jdwp_attach": jdwp_available or is_debuggable,
                "run_as_sandbox": is_debuggable,
                "heap_dump": is_debuggable,
            },
            "recent_errors": recent_errors,
            "recent_log_snippet": recent_logs[-500:] if recent_logs else ""
        }

        return diagnosis

    # -------------------------------------------------------------------------
    # FASE 9: Monitor de Problemas en Vivo (android.watch_app)
    # -------------------------------------------------------------------------

    def watch_app(
        self,
        package_name: str,
        duration: float = 10.0,
        check_interval: float = 1.0,
        evidence_dir: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Monitorea activamente una aplicación en ejecución para detectar anomalías:
        - Crashes / Fatal Exceptions
        - ANRs
        - Force-stops o muertes de proceso
        - Transiciones de actividad
        Guarda evidencia estructurada (capturas, dumpsys, logs) si se detecta un incidente.
        """
        if not evidence_dir:
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            evidence_dir = os.path.join(r"I:\Proyectos\HermesAndroid\tests\debug", timestamp)

        events: List[Dict[str, Any]] = []
        initial_pid = self.get_app_pid(package_name)
        initial_fg = self.controller.get_foreground_app()
        
        start_time = time.time()
        last_activity = initial_fg.get("activity")
        crash_detected = False

        while time.time() - start_time < duration:
            current_pid = self.get_app_pid(package_name)
            current_fg = self.controller.get_foreground_app()
            current_activity = current_fg.get("activity") if current_fg.get("package") == package_name else "background"

            # 1. Detectar pérdida o cambio inesperado de PID
            if initial_pid and not current_pid:
                events.append({
                    "time": time.time() - start_time,
                    "event": "PROCESS_TERMINATED",
                    "details": f"El proceso con PID {initial_pid} ha finalizado."
                })
                initial_pid = None
            elif current_pid and current_pid != initial_pid:
                events.append({
                    "time": time.time() - start_time,
                    "event": "PROCESS_RESTARTED",
                    "details": f"El proceso se reinició con nuevo PID {current_pid} (anterior: {initial_pid})."
                })
                initial_pid = current_pid

            # 2. Detectar cambio de actividad
            if current_activity != last_activity:
                events.append({
                    "time": time.time() - start_time,
                    "event": "ACTIVITY_CHANGED",
                    "details": f"Actividad cambió de '{last_activity}' a '{current_activity}'."
                })
                last_activity = current_activity

            # 3. Detectar crashes o excepciones en logcat
            errors = self.get_recent_errors(package_name=package_name, lines=50)
            if errors:
                crash_detected = True
                for err in errors:
                    events.append({
                        "time": time.time() - start_time,
                        "event": "CRASH_DETECTED",
                        "details": err.get("header", "Excepción fatal detectada.")
                    })
                break

            time.sleep(check_interval)

        # Si hubo eventos anómalos o crash, recopilar evidencia estructurada
        evidence_saved = False
        if events or crash_detected:
            os.makedirs(evidence_dir, exist_ok=True)
            # 1. Guardar captura de pantalla
            try:
                ss_path = os.path.join(evidence_dir, "incident_screenshot.png")
                self.controller.screenshot(ss_path)
            except Exception:
                pass

            # 2. Guardar dump de logs
            logs_path = os.path.join(evidence_dir, "incident_logcat.txt")
            with open(logs_path, "w", encoding="utf-8") as f:
                f.write(self.logcat(lines=300))

            # 3. Guardar dumpsys activity
            dump_path = os.path.join(evidence_dir, "incident_dumpsys.txt")
            with open(dump_path, "w", encoding="utf-8") as f:
                f.write(self.dumpsys("activity"))

            evidence_saved = True

        return {
            "package": package_name,
            "duration": duration,
            "initial_pid": initial_pid,
            "final_pid": self.get_app_pid(package_name),
            "crash_detected": crash_detected,
            "events": events,
            "evidence_saved": evidence_saved,
            "evidence_dir": evidence_dir if evidence_saved else None
        }

    # ==========================================
    # CAPACIDADES DE LABORATORIO Y MITM (HERMESLAB)
    # ==========================================

    def root_status(self) -> Dict[str, Any]:
        """
        Verifica el estado y nivel de privilegios root en el dispositivo actual.
        """
        code, out, err = self.controller.run_shell("su -c id", timeout=10)
        if code == 0 and "uid=0" in out:
            return {
                "active": True,
                "identity": out.strip(),
                "uid": 0,
                "context": "root"
            }
        return {
            "active": False,
            "identity": out.strip() if out else err.strip(),
            "uid": None,
            "context": "unprivileged"
        }

    def magisk_status(self) -> Dict[str, Any]:
        """
        Verifica la presencia, versión y estado del entorno Magisk en el dispositivo.
        """
        code_v, out_v, _ = self.controller.run_shell("su -c magisk -v", timeout=10)
        code_c, out_c, _ = self.controller.run_shell("su -c magisk -V", timeout=10)
        code_m, out_m, _ = self.controller.run_shell("su -c ls -1 /data/adb/modules", timeout=10)

        is_installed = (code_v == 0 and bool(out_v.strip()))
        modules = [m.strip() for m in out_m.strip().splitlines() if m.strip()] if code_m == 0 else []

        return {
            "installed": is_installed,
            "version": out_v.strip() if is_installed else None,
            "version_code": out_c.strip() if is_installed else None,
            "active_modules": modules
        }

    def reqable_status(self) -> Dict[str, Any]:
        """
        Verifica el estado de instalación, versión, certificado CA y captura de Reqable.
        """
        pkg_info = self.get_package_info("com.reqable.android")
        is_installed = pkg_info.get("installed", False)
        
        # Comprobar si el proceso de Reqable está en ejecución
        pid = self.get_app_pid("com.reqable.android")
        
        # Comprobar si el certificado CA está en el almacén del sistema
        code_cert, out_cert, _ = self.controller.run_shell("ls /system/etc/security/cacerts/e94fb6b0.0", timeout=10)
        cert_installed = (code_cert == 0 and "e94fb6b0.0" in out_cert)

        # Comprobar si hay una interfaz VPN activa (típica de captura Reqable)
        code_vpn, out_vpn, _ = self.controller.run_shell("ip link show tun0", timeout=10)
        capture_active = (code_vpn == 0 and "tun0" in out_vpn)

        return {
            "installed": is_installed,
            "version_name": pkg_info.get("version_name"),
            "running": (pid is not None),
            "pid": pid,
            "ca_certificate_system": cert_installed,
            "ca_certificate_name": "e94fb6b0.0",
            "capture_active": capture_active
        }

    def reqable_start_capture(self) -> bool:
        """
        Inicia Reqable y asegura el inicio de la captura de tráfico.
        """
        self.controller.open_app("com.reqable.android")
        time.sleep(2)
        # Pulsar botón flotante de grabación si no está activa la VPN
        status = self.reqable_status()
        if not status.get("capture_active"):
            self.controller.tap(951, 2145)
            time.sleep(2)
        return True

    def reqable_stop_capture(self) -> bool:
        """
        Detiene la captura de tráfico en Reqable.
        """
        status = self.reqable_status()
        if status.get("capture_active"):
            self.controller.open_app("com.reqable.android")
            time.sleep(1)
            self.controller.tap(951, 2145)
            time.sleep(1)
        return True

    def reqable_export_module(self, dest_path: Optional[str] = None) -> Optional[str]:
        """
        Exporta el módulo Magisk de certificado CA desde el dispositivo hacia el almacenamiento de I:.
        """
        if not dest_path:
            dest_path = r"I:\Proyectos\HermesAndroid\lab\modules\reqable-magisk.zip"
        
        # Buscar en /sdcard/Download/Reqable/
        code, out, _ = self.controller.run_shell("ls /sdcard/Download/Reqable/reqable-magisk.zip")
        if code == 0:
            os.makedirs(os.path.dirname(dest_path), exist_ok=True)
            self.controller.run_adb(["pull", "/sdcard/Download/Reqable/reqable-magisk.zip", dest_path])
            if os.path.exists(dest_path):
                return dest_path
        return None

    def lab_status(self) -> Dict[str, Any]:
        """
        Retorna el informe consolidado del estado de salud y capacidades de HermesLab.
        """
        dev = self.controller.get_device_info()
        root = self.root_status()
        magisk = self.magisk_status()
        reqable = self.reqable_status()

        return {
            "device": dev.get("model", "Unknown"),
            "serial": self.controller.serial,
            "android_version": dev.get("android_version"),
            "api_level": dev.get("sdk_version"),
            "root": root,
            "magisk": magisk,
            "reqable": reqable,
            "ready_for_traffic_analysis": (root.get("active") and reqable.get("ca_certificate_system"))
        }

