"""
Prueba formal de Misión de Navegación Segura en HermesPhone.
Ejecuta la misión 'test_hermesphone_navigation' con todas las fases de auditoría y evidencia.
"""

import os
import sys
import unittest
import json

# Asegurar import de módulos de hermes_android
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_DIR = os.path.join(PROJECT_ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)
from hermes_android import HermesAndroidAgent, Mission, MissionStep


class TestHermesPhoneNavigationMission(unittest.TestCase):

    def setUp(self):
        self.agent = HermesAndroidAgent()

    def test_full_navigation_mission(self):
        # Comprobar si hay dispositivo online antes de ejecutar integración real
        devs = self.agent.list_devices()
        if not any(d.get("state") == "ONLINE" for d in devs):
            self.skipTest("No hay dispositivo o emulador Android ONLINE. Prueba de integración omitida.")

        # Definición formal de la misión
        mission = Mission(
            name="test_hermesphone_navigation",
            device="HermesPhone",
            description="Misión de navegación segura y reversible: Settings -> Network & internet -> Back -> Home",
            steps=[
                # 1. Asegurar arranque y verificación de boot
                MissionStep(
                    step_id="STEP_01_BOOT",
                    action="verify",
                    expected_state={"is_boot_completed": True},
                    timeout=60.0
                ),
                # 2. Screenshot inicial
                MissionStep(
                    step_id="STEP_02_INITIAL_SCREENSHOT",
                    action="screenshot"
                ),
                # 3. Abrir Android Settings
                MissionStep(
                    step_id="STEP_03_OPEN_SETTINGS",
                    action="open_app",
                    target="com.android.settings",
                    wait_for="Network & internet",
                    expected_state={"foreground_package": "com.android.settings"}
                ),
                # 4. Esperar y verificar UI de Settings
                MissionStep(
                    step_id="STEP_04_VERIFY_SETTINGS_UI",
                    action="verify",
                    expected_state={"ui_contains_text": "Network & internet"}
                ),
                # 5. Localizar y pulsar elemento reversible (Network & internet)
                MissionStep(
                    step_id="STEP_05_TAP_NETWORK_SETTINGS",
                    action="tap_element",
                    target="Network & internet",
                    timeout=10.0
                ),
                # 6. Verificar nuevo estado (pantalla Network & internet con Airplane mode o Internet)
                MissionStep(
                    step_id="STEP_06_VERIFY_NETWORK_SCREEN",
                    action="verify",
                    expected_state={"ui_contains_text": "Airplane mode"},
                    retry=3
                ),
                # 7. Screenshot de la sección Network
                MissionStep(
                    step_id="STEP_07_SCREENSHOT_NETWORK",
                    action="screenshot"
                ),
                # 8. Pulsar Back para regresar
                MissionStep(
                    step_id="STEP_08_PRESS_BACK",
                    action="back"
                ),
                # 9. Verificar regreso al menú principal de Settings
                MissionStep(
                    step_id="STEP_09_VERIFY_RETURN_SETTINGS",
                    action="verify",
                    expected_state={"ui_contains_text": "Network & internet"}
                ),
                # 10. Pulsar Home
                MissionStep(
                    step_id="STEP_10_PRESS_HOME",
                    action="home"
                ),
                # 11. Captura final en launcher / home
                MissionStep(
                    step_id="STEP_11_FINAL_SCREENSHOT",
                    action="screenshot"
                ),
                # 12. Verificación final de estado saludable
                MissionStep(
                    step_id="STEP_12_FINAL_HEALTH_CHECK",
                    action="verify",
                    expected_state={"is_boot_completed": True}
                )
            ]
        )

        # Ejecutar misión a través del Mission Engine
        report = self.agent.run_mission(mission)

        # Validaciones de auditoría
        self.assertTrue(report.success, f"La misión falló: {report.error_summary}")
        self.assertEqual(report.failed_steps, 0, f"Hubo {report.failed_steps} pasos fallidos.")
        self.assertEqual(report.successful_steps, len(mission.steps))
        self.assertTrue(os.path.exists(report.evidence_dir), f"Directorio de evidencia no existe: {report.evidence_dir}")

        # Comprobar existencia de artefactos requeridos
        self.assertTrue(os.path.exists(os.path.join(report.evidence_dir, "mission.json")))
        self.assertTrue(os.path.exists(os.path.join(report.evidence_dir, "run.log")))
        self.assertTrue(os.path.exists(os.path.join(report.evidence_dir, "verification_results.json")))
        self.assertTrue(os.path.exists(os.path.join(report.evidence_dir, "report.json")))
        self.assertTrue(os.path.exists(os.path.join(report.evidence_dir, "report.md")))

        # Comprobar screenshots generados
        shots = os.listdir(os.path.join(report.evidence_dir, "screenshots"))
        self.assertGreaterEqual(len(shots), 10, "Se esperaba evidencia visual de todos los pasos.")

        print(f"\n==================================================")
        print(f"TEST PASSED: {report.mission_name}")
        print(f"Evidencia guardada en: {report.evidence_dir}")
        print(f"Duración: {report.duration_s:.2f}s")
        print(f"==================================================\n")


if __name__ == "__main__":
    unittest.main()
