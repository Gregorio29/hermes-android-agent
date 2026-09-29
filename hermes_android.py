"""
HERMES ANDROID AGENT — Punto de Entrada Principal (v2.0.0).
Reenvía y expone la API completa de HermesAndroidAgent desde python/hermes_android.py.
"""

import os
import sys

# Agregar carpeta python/ al sys.path
PYTHON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python")
if PYTHON_DIR not in sys.path:
    sys.path.insert(0, PYTHON_DIR)

from hermes_android import (
    HermesAndroidAgent,
    DeviceInfo,
    DeviceType,
    DeviceState,
    UIElement,
    Mission,
    MissionStep,
    StepResult,
    MissionReport,
    SecurityPolicy,
    SecurityLevel,
    DeviceRegistry,
    LifecycleManager,
    AndroidController,
    MissionEngine,
    main
)

if __name__ == "__main__":
    main()
