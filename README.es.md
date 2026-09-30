# Hermes Android Agent Toolkit

[English](README.md) | [Español](README.es.md)

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Android](https://img.shields.io/badge/Android%20SDK-ADB%20%26%20UIAutomator-green.svg)](https://developer.android.com/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/Tests-8%20Passed%20%7C%202%20Skipped-green.svg)](#)

Un toolkit modular, seguro y listo para producción para la automatización e inspección de dispositivos Android diseñado específicamente para agentes autónomos de inteligencia artificial. Proporciona volcado profundo de jerarquías de interfaz (conversión de XML a modelos espaciales), inyección de eventos, control de ciclo de vida de aplicaciones, gestión multi-dispositivo (físicos y emuladores AVD) y políticas operacionales de seguridad.

---

## 📱 Características Principales

- **Registro y Descubrimiento de Dispositivos:** Descubre automáticamente dispositivos físicos conectados mediante ADB y emuladores virtuales AVD configurados con resolución inteligente de alias.
- **Jerarquía de UI e Inspección Espacial:** Vuelca y parsea árboles de accesibilidad de Android en modelos `UIElement` estructurados con cajas delimitadoras (bounds), coordenadas de centro e indicadores de interacción.
- **Filtro Operacional de Seguridad (`security.py`):** Clasifica las acciones en niveles `SAFE`, `REVERSIBLE`, `SENSITIVE` y `DESTRUCTIVE`, bloqueando fugas de credenciales y operaciones destructivas por defecto.
- **Motor de Ejecución de Misiones:** Ejecuta flujos de automatización verificables (`MissionStep`) con aserciones de estado, reintentos automáticos, captura de evidencias visuales y registros de auditoría.
- **Arquitectura Limpia:** Totalmente desacoplado de imágenes pesadas de emuladores, volcados de APKs o discos binarios del sistema.

---

## 🛠️ Estructura del Proyecto

```text
HermesAndroid/
├── python/
│   ├── android_controller.py  # Ejecución ADB, tap, swipe, input, keyevents
│   ├── debug_controller.py    # Inspección de logcat, detección de crash, diagnóstico APK
│   ├── device_registry.py     # Descubrimiento multi-dispositivo y alias
│   ├── hermes_android.py      # Interfaz unificada de agente
│   ├── lifecycle.py           # Control de arranque, snapshot y apagado de emuladores
│   ├── mission_engine.py      # Ejecutor estructurado de misiones y reportes
│   ├── models.py              # Modelos de datos (DeviceInfo, UIElement, Mission, StepResult)
│   └── security.py            # Validación de niveles de seguridad y control de acciones
├── docs/                      # Referencias técnicas y análisis de root
├── examples/                  # Ejemplos de integración en Python
├── scripts/                   # Scripts auxiliares PowerShell de inicio y verificación
├── tests/                     # Suite de pruebas unitarias e integración
├── hermes_android.py          # Punto de entrada principal
├── requirements.txt           # Dependencias Python
└── LICENSE                    # Licencia MIT
```

---

## 📦 Instalación y Requisitos Previos

1. Asegúrate de tener instalado el Android SDK platform-tools (`adb`) en el `PATH` (o configurar `ANDROID_HOME`).
2. Clona este repositorio:
```bash
git clone https://github.com/Gregorio29/hermes-android-agent.git
cd hermes-android-agent
pip install -r requirements.txt
```

---

## 💻 Uso desde la CLI

### Descubrir Dispositivos Conectados
```bash
python hermes_android.py list-devices
```

### Capturar Pantalla
```bash
python hermes_android.py screenshot --device HermesPhone --output screen.png
```

### Inspeccionar Jerarquía de UI
```bash
python hermes_android.py dump-ui --device HermesPhone
```

---

## 🐍 Uso como Librería Python

```python
from python.hermes_android import HermesAndroidAgent

agent = HermesAndroidAgent()
agent.select_device("HermesPhone")

# Capturar pantalla de forma segura
screenshot_path = agent.screenshot()
print(f"Captura guardada en: {screenshot_path}")

# Pulsar sobre un elemento de la pantalla por su texto
agent.tap_element(target="Settings")
```

---

## 🧪 Ejecución de Pruebas Unitarias

```bash
python -m unittest discover -s tests -p "test_*.py"
```
*Nota sobre la suite de pruebas:* Ejecuta 10 casos de prueba (8 pruebas unitarias que validan modelos, registro y políticas de seguridad pasan automáticamente; 2 pruebas de integración con hardware que requieren un dispositivo/emulador activo son omitidas limpiamente cuando no hay un dispositivo online).

---

## 📄 Licencia

Este proyecto está distribuido bajo la [Licencia MIT](LICENSE).
