"""
Misión de Diagnóstico y Laboratorio en HermesLab (test_hermeslab_debug).
Ejecuta el ciclo completo de validación en HermesLab:
1. Verificación de boot y estado de HermesLab.
2. Instalación de HermesDebugTarget.
3. Diagnóstico estático y dinámico de paquete (Black Box vs Debuggable).
4. Lanzamiento y validación de UI.
5. Ejecución de actividad normal e inspección de logs.
6. Disparo de crash controlado e intercepción de excepción en logcat.
7. Auditoría de evidencia y cierre seguro.
"""

import os
import sys
import time
import unittest

# Asegurar importaciones desde la carpeta python/
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "python")))

from models import Mission, MissionStep, DeviceType, DeviceState
from device_registry import DeviceRegistry
from lifecycle import LifecycleManager
from android_controller import AndroidController
from mission_engine import MissionEngine


class TestHermesLabDebugMission(unittest.TestCase):
    """Prueba automatizada de la misión de diagnóstico y pruebas en HermesLab."""

    @classmethod
    def setUpClass(cls):
        cls.registry = DeviceRegistry()
        cls.lifecycle = LifecycleManager(cls.registry)
        cls.controller = AndroidController(cls.registry)
        cls.engine = MissionEngine(cls.registry, cls.lifecycle, cls.controller)
        cls.apk_path = r"I:\Proyectos\HermesAndroid\debug\HermesDebugTarget.apk"
        cls.pkg_name = "com.hermes.debugtarget"

        if not os.path.exists(cls.apk_path):
            raise unittest.SkipTest(f"APK de prueba no disponible en entorno de tests: {cls.apk_path}")

    def test_hermeslab_debug_mission(self):
        """Construye y ejecuta la misión test_hermeslab_debug en HermesLab."""
        dev = self.registry.select_device("HermesLab")
        if not dev or dev.state != DeviceState.READY:
            self.skipTest("Dispositivo HermesLab no está disponible o READY en el entorno.")
        mission = Mission(
            name="test_hermeslab_debug",
            device="HermesLab",
            description="Validación de ciclo de vida, instalación APK, UI, logs, crash controlado y evidencias en HermesLab",
            steps=[
                MissionStep(
                    step_id="STEP_01_BOOT_CHECK",
                    action="verify",
                    expected_state={"is_boot_completed": True}
                ),
                MissionStep(
                    step_id="STEP_02_INSTALL_DEBUG_TARGET",
                    action="install_app",
                    target=self.apk_path,
                    expected_state={"package_installed": self.pkg_name}
                ),
                MissionStep(
                    step_id="STEP_03_DIAGNOSE_PACKAGE",
                    action="debug_app",
                    target=self.pkg_name,
                    expected_state={"package_installed": self.pkg_name}
                ),
                MissionStep(
                    step_id="STEP_04_LAUNCH_APP",
                    action="open_app",
                    target=self.pkg_name,
                    wait_for="Hermes Debug Target v2.0.0 (Lab)",
                    expected_state={"foreground_package": self.pkg_name}
                ),
                MissionStep(
                    step_id="STEP_05_VERIFY_UI_INITIAL",
                    action="verify",
                    expected_state={"ui_contains_text": "Status: IDLE"}
                ),
                MissionStep(
                    step_id="STEP_06_SIMULATE_NORMAL_ACTION",
                    action="tap_element",
                    target="Simulate Normal Action",
                    wait_for="Status: ACTION_EXECUTED",
                    expected_state={"ui_contains_text": "Status: ACTION_EXECUTED"}
                ),
                MissionStep(
                    step_id="STEP_07_CAPTURE_LOGS",
                    action="logcat",
                    parameters={"lines": 50}
                ),
                MissionStep(
                    step_id="STEP_08_TRIGGER_CONTROLLED_CRASH",
                    action="tap_element",
                    target="Trigger Controlled Crash"
                ),
                MissionStep(
                    step_id="STEP_09_VERIFY_CRASH_DETECTION",
                    action="verify",
                    expected_state={"is_boot_completed": True}
                ),
                MissionStep(
                    step_id="STEP_10_CLOSE_APP_AND_HOME",
                    action="home",
                    expected_state={"is_boot_completed": True}
                ),
                MissionStep(
                    step_id="STEP_11_FINAL_HEALTH_CHECK",
                    action="verify",
                    expected_state={"is_boot_completed": True}
                )
            ]
        )

        print(f"\n[TEST] Iniciando ejecución de misión: {mission.name} en HermesLab...")
        report = self.engine.run_mission(mission)

        # Aserciones de verificación formal
        self.assertTrue(report.success, f"La misión falló. Resumen: {report.error_summary}")
        self.assertEqual(report.failed_steps, 0, f"Pasos fallidos: {report.failed_steps}")
        self.assertEqual(report.successful_steps, len(mission.steps), "No todos los pasos fueron exitosos")
        self.assertTrue(os.path.exists(report.evidence_dir), "El directorio de evidencia no fue creado")
        self.assertTrue(os.path.exists(os.path.join(report.evidence_dir, "report.json")), "Falta report.json")
        self.assertTrue(os.path.exists(os.path.join(report.evidence_dir, "report.md")), "Falta report.md")

        print(f"[TEST] Misión completada exitosamente en {report.duration_s:.2f}s.")
        print(f"[TEST] Evidencias disponibles en: {report.evidence_dir}")


if __name__ == "__main__":
    unittest.main(verbosity=2)
