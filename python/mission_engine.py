"""
Motor de Ejecución de Misiones para Hermes Android (Mission Engine).
Orquesta el ciclo de vida, ejecución de pasos, verificación basada en estado real,
gestión de reintentos, control de seguridad operacional y almacenamiento de evidencia.
"""

import os
import json
import time
import logging
from typing import Dict, Any, Optional, List, Tuple, Union

from models import Mission, MissionStep, StepResult, MissionReport, DeviceState, DeviceType
from device_registry import DeviceRegistry
from lifecycle import LifecycleManager
from android_controller import AndroidController
from security import SecurityPolicy, SecurityLevel


class MissionEngine:
    """Motor central para la carga, ejecución y auditoría de misiones Android."""

    def __init__(
        self,
        registry: Optional[DeviceRegistry] = None,
        lifecycle: Optional[LifecycleManager] = None,
        controller: Optional[AndroidController] = None,
        security_policy: Optional[SecurityPolicy] = None,
        base_evidence_dir: str = r"I:\Proyectos\HermesAndroid\tests\missions"
    ):
        self.registry = registry or DeviceRegistry()
        self.lifecycle = lifecycle or LifecycleManager(self.registry)
        self.security_policy = security_policy or SecurityPolicy()
        self.controller = controller or AndroidController(self.registry, self.security_policy)
        self.base_evidence_dir = base_evidence_dir
        os.makedirs(self.base_evidence_dir, exist_ok=True)

    def _setup_run_directory(self, mission_name: str) -> Tuple[str, Dict[str, str]]:
        """Crea el directorio único de evidencia para la ejecución actual."""
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        safe_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in mission_name)
        run_dir = os.path.join(self.base_evidence_dir, f"{timestamp}_{safe_name}")
        
        paths = {
            "root": run_dir,
            "screenshots": os.path.join(run_dir, "screenshots"),
            "ui_xml": os.path.join(run_dir, "ui_xml"),
            "logs": os.path.join(run_dir, "logs"),
            "run_log": os.path.join(run_dir, "run.log"),
            "error_log": os.path.join(run_dir, "error.log"),
            "mission_json": os.path.join(run_dir, "mission.json"),
            "verification_json": os.path.join(run_dir, "verification_results.json"),
            "report_json": os.path.join(run_dir, "report.json"),
            "report_md": os.path.join(run_dir, "report.md")
        }
        
        for p in [paths["root"], paths["screenshots"], paths["ui_xml"], paths["logs"]]:
            os.makedirs(p, exist_ok=True)
            
        return run_dir, paths

    def _setup_logger(self, log_path: str) -> logging.Logger:
        """Configura un logger específico para la sesión de misión."""
        logger = logging.getLogger(f"Mission_{time.time()}")
        logger.setLevel(logging.INFO)
        logger.handlers.clear()

        # Handler de archivo
        fh = logging.FileHandler(log_path, encoding="utf-8")
        fh.setLevel(logging.INFO)
        formatter = logging.Formatter("[%(asctime)s] [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S")
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        # Handler de consola
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        return logger

    def load_mission(self, source: Union[Mission, Dict[str, Any], str]) -> Mission:
        """Carga una misión desde un objeto Mission, diccionario o archivo JSON."""
        if isinstance(source, Mission):
            return source
        elif isinstance(source, dict):
            return Mission.from_dict(source)
        elif isinstance(source, str):
            if os.path.exists(source):
                with open(source, "r", encoding="utf-8") as f:
                    data = json.load(f)
                return Mission.from_dict(data)
            else:
                # Tratar como JSON string
                data = json.loads(source)
                return Mission.from_dict(data)
        else:
            raise ValueError(f"Tipo de fuente de misión inválido: {type(source)}")

    def run_mission(self, mission_input: Union[Mission, Dict[str, Any], str]) -> MissionReport:
        """
        Ejecuta la misión completa paso a paso con verificación real y almacenamiento de evidencia.
        """
        mission = self.load_mission(mission_input)
        run_dir, paths = self._setup_run_directory(mission.name)
        logger = self._setup_logger(paths["run_log"])

        logger.info(f"==================================================")
        logger.info(f"INICIANDO MISIÓN: {mission.name}")
        logger.info(f"Dispositivo objetivo: {mission.device}")
        logger.info(f"Total pasos: {len(mission.steps)}")
        logger.info(f"Directorio de evidencia: {run_dir}")
        logger.info(f"==================================================")

        # Guardar copia de la definición de misión
        with open(paths["mission_json"], "w", encoding="utf-8") as f:
            json.dump(mission.to_dict(), f, indent=2, ensure_ascii=False)

        start_time = time.time()
        step_results: List[StepResult] = []
        mission_success = True
        error_summary: Optional[str] = None

        # 1. Asegurar selección y estado del dispositivo
        selected_dev = self.registry.select_device(mission.device)
        if not selected_dev:
            error_msg = f"Dispositivo '{mission.device}' no encontrado en el registro."
            logger.error(error_msg)
            return self._finalize_report(mission, False, 0, 0, len(mission.steps), time.time() - start_time, run_dir, [], error_msg, paths, logger)

        # Si el dispositivo es HermesPhone y está apagado, iniciarlo automáticamente
        status = self.lifecycle.device_status(mission.device)
        if not status.get("is_boot_completed"):
            logger.info(f"Dispositivo '{mission.device}' no está listo. Iniciando...")
            ok_start, start_msg = self.lifecycle.start_device(mission.device, timeout=120)
            if not ok_start:
                error_msg = f"Fallo al iniciar dispositivo: {start_msg}"
                logger.error(error_msg)
                return self._finalize_report(mission, False, 0, 0, len(mission.steps), time.time() - start_time, run_dir, [], error_msg, paths, logger)
            logger.info(start_msg)

        # 2. Ejecutar cada paso de la misión
        for idx, step in enumerate(mission.steps, 1):
            step_id = step.step_id or f"STEP_{idx:02d}"
            logger.info(f"\n>>> [{step_id}] ACTION: {step.action} | TARGET: {step.target}")

            step_start = time.time()
            allowed, sec_level, sec_reason = self.security_policy.check_action(step.action, step.target)
            
            if not allowed:
                err_sec = f"SEGURIDAD: Acción '{step.action}' denegada ({sec_level.value}): {sec_reason}"
                logger.error(err_sec)
                res = StepResult(
                    step_id=step_id,
                    action=step.action,
                    target=step.target,
                    success=False,
                    verification_passed=False,
                    details=err_sec,
                    duration_s=time.time() - step_start,
                    error_message=err_sec
                )
                step_results.append(res)
                mission_success = False
                error_summary = err_sec
                if step.on_failure == "ABORT":
                    break
                continue

            # Ejecutar con reintentos configurados
            success, verif_passed, details, shot_path, xml_path, err_msg = self._execute_step_with_retry(
                step=step,
                step_idx=idx,
                paths=paths,
                logger=logger
            )

            step_duration = time.time() - step_start
            res = StepResult(
                step_id=step_id,
                action=step.action,
                target=step.target,
                success=success,
                verification_passed=verif_passed,
                details=details,
                duration_s=step_duration,
                screenshot_path=shot_path,
                ui_xml_path=xml_path,
                error_message=err_msg
            )
            step_results.append(res)

            logger.info(f"[{step_id}] RESULT: {'SUCCESS' if success else 'FAILED'} | VERIFICATION: {'PASSED' if verif_passed else 'FAILED'} ({step_duration:.2f}s)")
            if details:
                logger.info(f"[{step_id}] DETAILS: {details}")

            if not success or not verif_passed:
                mission_success = False
                error_summary = f"Fallo en paso {step_id} ({step.action}): {err_msg or details}"
                logger.error(f"[{step_id}] ERROR: {error_summary}")
                
                # Guardar captura y log de error
                self._save_error_diagnostics(step_id, error_summary, paths, logger)
                
                if step.on_failure == "ABORT":
                    logger.warning(f"Abortando misión por política on_failure=ABORT en {step_id}")
                    break

        total_duration = time.time() - start_time
        successful_steps = sum(1 for r in step_results if r.success and r.verification_passed)
        failed_steps = len(step_results) - successful_steps

        return self._finalize_report(
            mission=mission,
            success=mission_success,
            total_steps=len(mission.steps),
            successful_steps=successful_steps,
            failed_steps=failed_steps,
            duration_s=total_duration,
            evidence_dir=run_dir,
            results=step_results,
            error_summary=error_summary,
            paths=paths,
            logger=logger
        )

    def _execute_step_with_retry(
        self,
        step: MissionStep,
        step_idx: int,
        paths: Dict[str, str],
        logger: logging.Logger
    ) -> Tuple[bool, bool, str, Optional[str], Optional[str], Optional[str]]:
        """Ejecuta un paso individual aplicando lógica de reintentos y captura de evidencias."""
        max_attempts = max(1, step.retry + 1)
        last_details = ""
        last_err = ""
        shot_path = None
        xml_path = None

        for attempt in range(1, max_attempts + 1):
            if attempt > 1:
                logger.info(f"Reintento {attempt}/{max_attempts} para {step.action}...")
                time.sleep(1.0)

            try:
                # 1. Ejecutar la acción
                action_success, action_details = self._dispatch_action(step)
                if not action_success:
                    last_err = f"Acción '{step.action}' falló: {action_details}"
                    continue

                # 2. Espera posterior si está configurada (wait_for)
                if step.wait_for:
                    wait_ok = self.controller.wait_for(step.wait_for, timeout=step.timeout)
                    if not wait_ok:
                        last_err = f"Timeout esperando elemento tras acción: {step.wait_for}"
                        continue

                # Breve pausa para estabilización de renderizado UI
                time.sleep(0.5)

                # 3. Captura de evidencia (Screenshot y UI XML)
                shot_filename = f"step_{step_idx:02d}_{step.action}.png"
                shot_path = os.path.join(paths["screenshots"], shot_filename)
                try:
                    self.controller.screenshot(shot_path)
                except Exception as e:
                    logger.warning(f"No se pudo guardar screenshot del paso {step_idx}: {e}")

                xml_filename = f"step_{step_idx:02d}_{step.action}.xml"
                xml_path = os.path.join(paths["ui_xml"], xml_filename)
                try:
                    _, raw_xml = self.controller.get_ui_tree()
                    with open(xml_path, "w", encoding="utf-8") as f:
                        f.write(raw_xml)
                except Exception as e:
                    logger.warning(f"No se pudo guardar UI XML del paso {step_idx}: {e}")

                # 4. Verificación de Estado Real (Truth Gating)
                if step.expected_state:
                    verif_ok, verif_msg = self.controller.verify(step.expected_state)
                    if not verif_ok:
                        last_err = f"Verificación falló: {verif_msg}"
                        continue
                    else:
                        last_details = f"{action_details} | Verificación OK: {verif_msg}"
                        return True, True, last_details, shot_path, xml_path, None
                else:
                    return True, True, action_details, shot_path, xml_path, None

            except Exception as e:
                last_err = f"Excepción durante ejecución de paso: {e}"

        return False, False, last_details, shot_path, xml_path, last_err

    def _dispatch_action(self, step: MissionStep) -> Tuple[bool, str]:
        """Despacha la acción al método correspondiente de AndroidController o LifecycleManager."""
        action = step.action.lower()
        target = step.target
        params = step.parameters

        if action in ("start_device", "boot"):
            target_dev = str(target) if target else "HermesPhone"
            ok, msg = self.lifecycle.start_device(target_dev, **params)
            return ok, msg

        elif action in ("stop_device", "shutdown"):
            target_dev = str(target) if target else "HermesPhone"
            ok, msg = self.lifecycle.stop_device(target_dev, **params)
            return ok, msg

        elif action in ("open_app", "launch_app"):
            pkg = str(target)
            activity = params.get("activity")
            ok = self.controller.open_app(pkg, activity=activity)
            return ok, f"Aplicación '{pkg}' lanzada."

        elif action in ("install_app", "install"):
            apk = str(target)
            replace = params.get("replace_existing", True)
            ok = self.controller.install_app(apk, replace_existing=replace)
            return ok, f"Instalación de '{apk}' {'completada' if ok else 'fallida'}."

        elif action in ("debug_app", "diagnose"):
            pkg = str(target)
            diag = self.controller.debug_app(pkg)
            return True, f"Diagnóstico obtenido para '{pkg}': status={diag.get('status')}, debugger={diag.get('debugger_attach')}"

        elif action in ("watch_app", "monitor"):
            pkg = str(target)
            dur = params.get("duration", 5.0)
            res = self.controller.watch_app(pkg, duration=dur)
            return True, f"Monitoreo finalizado en '{pkg}': crash_detected={res.get('crash_detected')}, eventos={len(res.get('events', []))}"

        elif action == "logcat":
            lines = params.get("lines", 100)
            logs = self.controller.logcat(lines=lines)
            return True, f"Logcat capturado ({len(logs.splitlines())} líneas)."

        elif action in ("close_app", "kill_app"):
            pkg = str(target)
            ok = self.controller.close_app(pkg)
            return ok, f"Aplicación '{pkg}' cerrada."

        elif action == "tap":
            if isinstance(target, (list, tuple)) and len(target) == 2:
                x, y = int(target[0]), int(target[1])
            elif "x" in params and "y" in params:
                x, y = int(params["x"]), int(params["y"])
            else:
                return False, "Coordenadas (x, y) requeridas para acción tap."
            ok = self.controller.tap(x, y)
            return ok, f"Tap ejecutado en ({x}, {y})."

        elif action == "tap_element":
            query = target or params
            ok = self.controller.tap_element(query)
            if ok:
                return True, f"Elemento '{query}' localizado y tocado."
            return False, f"No se pudo encontrar o tocar el elemento '{query}'."

        elif action == "swipe":
            x1 = params.get("x1", 500)
            y1 = params.get("y1", 1500)
            x2 = params.get("x2", 500)
            y2 = params.get("y2", 500)
            dur = params.get("duration_ms", 300)
            ok = self.controller.swipe(x1, y1, x2, y2, duration_ms=dur)
            return ok, f"Swipe de ({x1},{y1}) a ({x2},{y2}) ejecutado."

        elif action == "type":
            text = str(target if target is not None else params.get("text", ""))
            ok = self.controller.type(text)
            return ok, f"Texto escrito: '{text}'"

        elif action == "press":
            key = str(target if target is not None else params.get("key", "BACK"))
            ok = self.controller.press(key)
            return ok, f"Tecla presionada: '{key}'"

        elif action == "home":
            ok = self.controller.home()
            return ok, "Botón HOME presionado."

        elif action == "back":
            ok = self.controller.back()
            return ok, "Botón BACK presionado."

        elif action == "screenshot":
            # La captura se realiza automáticamente en el ciclo del paso
            return True, "Captura solicitada."

        elif action == "wait_for":
            query = target or params
            timeout = step.timeout
            ok = self.controller.wait_for(query, timeout=timeout)
            return ok, f"Espera de '{query}' completada con éxito." if ok else f"Timeout esperando '{query}'."

        elif action == "verify":
            expected = step.expected_state or (target if isinstance(target, dict) else {"ui_contains_text": str(target)})
            ok, msg = self.controller.verify(expected)
            return ok, msg

        else:
            return False, f"Acción no reconocida: '{step.action}'"

    def _save_error_diagnostics(self, step_id: str, error_msg: str, paths: Dict[str, str], logger: logging.Logger):
        """Guarda información diagnóstica de error en error.log."""
        try:
            fg = self.controller.get_foreground_app()
            diag = {
                "step_id": step_id,
                "error": error_msg,
                "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
                "foreground_app": fg,
            }
            with open(paths["error_log"], "a", encoding="utf-8") as f:
                f.write(json.dumps(diag, indent=2, ensure_ascii=False) + "\n---\n")
        except Exception as e:
            logger.warning(f"No se pudo guardar error.log: {e}")

    def _finalize_report(
        self,
        mission: Mission,
        success: bool,
        total_steps: int,
        successful_steps: int,
        failed_steps: int,
        duration_s: float,
        evidence_dir: str,
        results: List[StepResult],
        error_summary: Optional[str],
        paths: Dict[str, str],
        logger: logging.Logger
    ) -> MissionReport:
        """Construye y almacena los reportes finales en JSON y Markdown."""
        report = MissionReport(
            mission_name=mission.name,
            device=mission.device,
            success=success,
            total_steps=total_steps,
            successful_steps=successful_steps,
            failed_steps=failed_steps,
            duration_s=duration_s,
            evidence_dir=evidence_dir,
            steps_results=results,
            error_summary=error_summary
        )

        # 1. Guardar report.json
        with open(paths["report_json"], "w", encoding="utf-8") as f:
            json.dump(report.to_dict(), f, indent=2, ensure_ascii=False)

        # 2. Guardar verification_results.json
        verif_data = [
            {
                "step_id": r.step_id,
                "action": r.action,
                "target": r.target,
                "passed": r.verification_passed,
                "details": r.details,
                "error": r.error_message
            }
            for r in results
        ]
        with open(paths["verification_json"], "w", encoding="utf-8") as f:
            json.dump(verif_data, f, indent=2, ensure_ascii=False)

        # 3. Guardar report.md
        md_content = f"""# INFORME DE MISIÓN: {mission.name}

- **Estado:** {'✅ EXITOSA' if success else '❌ FALLIDA'}
- **Dispositivo:** {mission.device}
- **Pasos Totales:** {total_steps} (Exitosos: {successful_steps}, Fallidos: {failed_steps})
- **Duración:** {duration_s:.2f}s
- **Directorio de Evidencia:** `{evidence_dir}`
- **Fecha:** {time.strftime('%Y-%m-%d %H:%M:%S')}

---

## Detalle de Pasos Ejecutados

| Paso | Acción | Target | Resultado | Verificación | Duración |
|------|--------|--------|-----------|--------------|----------|
"""
        for r in results:
            res_icon = "✅ OK" if r.success else "❌ FAIL"
            ver_icon = "✅ PASSED" if r.verification_passed else "❌ FAILED"
            target_str = str(r.target) if r.target is not None else "-"
            md_content += f"| `{r.step_id}` | `{r.action}` | `{target_str}` | {res_icon} | {ver_icon} | {r.duration_s:.2f}s |\n"

        if error_summary:
            md_content += f"\n## Resumen de Errores\n> ⚠️ {error_summary}\n"

        with open(paths["report_md"], "w", encoding="utf-8") as f:
            f.write(md_content)

        logger.info(f"\n==================================================")
        logger.info(f"MISIÓN FINALIZADA: {'EXITOSA' if success else 'FALLIDA'}")
        logger.info(f"Pasos: {successful_steps}/{total_steps} exitosos en {duration_s:.2f}s")
        logger.info(f"Reporte guardado en: {paths['report_md']}")
        logger.info(f"==================================================\n")

        return report
