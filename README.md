# Hermes Android Agent Toolkit

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Android](https://img.shields.io/badge/Android%20SDK-ADB%20%26%20UIAutomator-green.svg)](https://developer.android.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-10%20Passed-green.svg)](#)

A modular, secure, and production-grade Android device automation and inspection toolkit tailored for autonomous AI agents. Provides deep UI hierarchy dumping (XML to spatial objects), event injection, application lifecycle control, multi-device management (physical & virtual AVDs), and operational security policies.

---

## 📱 Key Features

- **Device Registry & Discovery:** Automatically discovers physical devices via ADB and configured virtual AVDs with alias resolution.
- **UI Hierarchy & Spatial Inspection:** Dumps and parses Android accessibility node hierarchies into structured `UIElement` models with bounding boxes, center coordinates, and interaction flags.
- **Operational Security Gate (`security.py`):** Classifies actions into `SAFE`, `REVERSIBLE`, `SENSITIVE`, and `DESTRUCTIVE`, blocking credential leaks or destructive operations by default.
- **Mission Execution Engine:** Executes multi-step verifiable automation workflows (`MissionStep`) with assertions, retry mechanics, screenshot evidence, and audit logs.
- **Clean Architecture:** Completely decoupled from bulky emulator images, APK dumps, or system binary disks.

---

## 🛠️ Project Structure

```text
HermesAndroid/
├── python/
│   ├── android_controller.py  # ADB execution, tap, swipe, input, keyevents
│   ├── debug_controller.py    # Logcat inspection, crash detection, APK diagnostics
│   ├── device_registry.py     # Multi-device discovery & alias resolution
│   ├── hermes_android.py      # Unified facade agent interface
│   ├── lifecycle.py           # Emulator boot, snapshot, and shutdown control
│   ├── mission_engine.py      # Structured mission runner & report generator
│   ├── models.py              # Data models (DeviceInfo, UIElement, Mission, StepResult)
│   └── security.py            # Security level validation and action gating
├── docs/                      # Technical references & root analysis
├── examples/                  # Python integration examples
├── scripts/                   # PowerShell launch & verification helpers
├── tests/                     # Unit & integration test suite
├── hermes_android.py          # Root entrypoint
├── requirements.txt           # Python dependencies
└── LICENSE                    # MIT License
```

---

## 📦 Installation & Prerequisites

1. Ensure the Android SDK platform-tools (`adb`) are installed and added to `PATH` (or set `ANDROID_HOME`).
2. Clone this repository:
```bash
git clone https://github.com/<username>/hermes-android-agent.git
cd hermes-android-agent
pip install -r requirements.txt
```

---

## 💻 CLI Usage

### Discover Connected Devices
```bash
python hermes_android.py list-devices
```

### Capture Screenshot
```bash
python hermes_android.py screenshot --device HermesPhone --output screen.png
```

### Inspect UI Hierarchy
```bash
python hermes_android.py dump-ui --device HermesPhone
```

---

## 🐍 Python Library Usage

```python
from python.hermes_android import HermesAndroidAgent

agent = HermesAndroidAgent()
agent.select_device("HermesPhone")

# Capture screenshot safely
screenshot_path = agent.screenshot()
print(f"Captured: {screenshot_path}")

# Tap on a screen element by text
agent.tap_element(target="Settings")
```

---

## 🧪 Running Tests

```bash
python -m unittest discover -s tests -p "test_*.py"
```

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
