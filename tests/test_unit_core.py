"""
Unit tests for HermesAndroid models, security policies, and device registry.
"""

import os
import sys
import unittest

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYTHON_DIR = os.path.join(PROJECT_ROOT, "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)

from models import (
    DeviceInfo, DeviceType, DeviceState, UIElement,
    Mission, MissionStep, StepResult, MissionReport
)
from security import SecurityPolicy, SecurityLevel, ACTION_SECURITY_MAP
from device_registry import DeviceRegistry


class TestHermesAndroidCore(unittest.TestCase):

    def test_device_info_model(self):
        device = DeviceInfo(
            name="HermesPhone",
            device_type=DeviceType.VIRTUAL_HERMES_PHONE,
            serial="emulator-5554",
            model="sdk_gphone64_x86_64",
            brand="google",
            android_version="14",
            sdk_level=34,
            state=DeviceState.ONLINE
        )
        self.assertEqual(device.name, "HermesPhone")
        self.assertEqual(device.state, DeviceState.ONLINE)
        self.assertEqual(device.device_type, DeviceType.VIRTUAL_HERMES_PHONE)
        dict_rep = device.to_dict()
        self.assertEqual(dict_rep["serial"], "emulator-5554")

    def test_ui_element_parsing(self):
        elem = UIElement(
            index="0",
            text="Settings",
            resource_id="com.android.settings:id/title",
            class_name="android.widget.TextView",
            package="com.android.settings",
            bounds="[100,200][300,300]",
            bounds_coords=(100, 200, 300, 300),
            center_x=200,
            center_y=250,
            clickable=True
        )
        self.assertEqual(elem.center_x, 200)
        self.assertEqual(elem.center_y, 250)
        self.assertEqual(elem.text, "Settings")
        self.assertTrue(elem.clickable)
        dict_rep = elem.to_dict()
        self.assertEqual(dict_rep["center"], [200, 250])

    def test_security_policy_classification(self):
        # Default policy blocks sensitive and destructive
        policy = SecurityPolicy(allow_sensitive=False, allow_destructive=False)
        
        # screenshot is SAFE -> allowed
        allowed, level, reason = policy.check_action("screenshot")
        self.assertTrue(allowed)
        self.assertEqual(level, SecurityLevel.SAFE)
        
        # uninstall_app is DESTRUCTIVE -> blocked
        allowed, level, reason = policy.check_action("uninstall_app")
        self.assertFalse(allowed)
        self.assertEqual(level, SecurityLevel.DESTRUCTIVE)

    def test_device_registry_lookup(self):
        registry = DeviceRegistry()
        dev_info = registry.select_device("hermesphone")
        if dev_info:
            self.assertEqual(dev_info.name, "HermesPhone")
            self.assertEqual(dev_info.device_type, DeviceType.VIRTUAL_HERMES_PHONE)


if __name__ == "__main__":
    unittest.main()
