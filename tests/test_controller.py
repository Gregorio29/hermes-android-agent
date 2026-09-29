"""
Pruebas unitarias y de integración para HermesAndroidAgent (Controller).
Verifica inicialización de rutas, alias, detección de SDK y métodos de control.
"""

import os
import sys
import unittest

# Asegurar import de módulo python
import os, sys
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_DIR = os.path.join(PROJECT_ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)
from hermes_android import HermesAndroidAgent


class TestHermesAndroidAgent(unittest.TestCase):

    def setUp(self):
        self.agent = HermesAndroidAgent()

    def test_sdk_location(self):
        self.assertTrue(os.path.exists(self.agent.sdk_dir), f"SDK dir no existe: {self.agent.sdk_dir}")
        self.assertTrue(os.path.exists(self.agent.adb_path), f"ADB no existe: {self.agent.adb_path}")
        self.assertTrue(os.path.exists(self.agent.emulator_path), f"Emulator no existe: {self.agent.emulator_path}")

    def test_device_selection_aliases(self):
        # HermesPhone virtual
        self.assertTrue(self.agent.select_device("HermesPhone"))
        self.assertEqual(self.agent.device_serial, "emulator-5554")

        self.assertTrue(self.agent.select_device("VIRTUAL_HERMES_PHONE"))
        self.assertEqual(self.agent.device_serial, "emulator-5554")

        # Samsung A71 físico
        self.assertTrue(self.agent.select_device("PHYSICAL_A71"))
        self.assertEqual(self.agent.device_serial, "R58NB0LWKAJ")

        self.assertTrue(self.agent.select_device("SAMSUNG_A71"))
        self.assertEqual(self.agent.device_serial, "R58NB0LWKAJ")

    def test_list_devices_shape(self):
        devs = self.agent.list_devices()
        self.assertIsInstance(devs, list)


if __name__ == "__main__":
    unittest.main()
