"""
Prueba de integridad y persistencia para HermesPhone AVD.
Verifica que la configuración del AVD mantenga compatibilidad si existe en el entorno.
"""

import os
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestHermesPersistence(unittest.TestCase):

    def setUp(self):
        self.base_avd_dir = os.environ.get("HERMES_AVD_DIR", r"I:\Proyectos\HermesAndroid\avd")
        self.avd_ini = os.path.join(self.base_avd_dir, "HermesPhone.ini")
        self.avd_folder = os.path.join(self.base_avd_dir, "HermesPhone.avd")
        self.config_ini = os.path.join(self.avd_folder, "config.ini")

    def test_avd_config_parameters_if_present(self):
        if not os.path.exists(self.config_ini):
            self.skipTest(f"AVD no configurado en entorno local ({self.config_ini})")
        
        with open(self.config_ini, "r", encoding="utf-8") as f:
            lines = [line.strip() for line in f if "=" in line and not line.startswith("#")]
        
        cfg = dict(line.split("=", 1) for line in lines)
        self.assertEqual(cfg.get("hw.cpu.arch"), "x86_64")


if __name__ == "__main__":
    unittest.main()
