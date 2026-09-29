"""
Modelos de datos para el sistema Hermes Android.
Contiene clases para Dispositivos, Pasos de Misión, Misiones e Informes.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional
import time


class DeviceType(str, Enum):
    PHYSICAL_A71 = "PHYSICAL_A71"
    VIRTUAL_HERMES_PHONE = "VIRTUAL_HERMES_PHONE"
    VIRTUAL_HERMES_LAB = "VIRTUAL_HERMES_LAB"
    GENERIC_PHYSICAL = "GENERIC_PHYSICAL"
    GENERIC_VIRTUAL = "GENERIC_VIRTUAL"


class DeviceState(str, Enum):
    OFFLINE = "OFFLINE"
    BOOTING = "BOOTING"
    ONLINE = "ONLINE"
    READY = "READY"
    UNAUTHORIZED = "UNAUTHORIZED"
    UNKNOWN = "UNKNOWN"


@dataclass
class DeviceInfo:
    """Información completa de un dispositivo Android registrado o detectado."""
    name: str
    device_type: DeviceType
    serial: Optional[str] = None
    model: Optional[str] = None
    brand: Optional[str] = None
    android_version: Optional[str] = None
    sdk_level: Optional[int] = None
    state: DeviceState = DeviceState.UNKNOWN
    is_powered_on: bool = False
    is_boot_completed: bool = False
    avd_name: Optional[str] = None
    avd_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "device_type": self.device_type.value,
            "serial": self.serial,
            "model": self.model,
            "brand": self.brand,
            "android_version": self.android_version,
            "sdk_level": self.sdk_level,
            "state": self.state.value,
            "is_powered_on": self.is_powered_on,
            "is_boot_completed": self.is_boot_completed,
            "avd_name": self.avd_name,
            "avd_path": self.avd_path,
        }


@dataclass
class UIElement:
    """Representación de un nodo de la jerarquía de UI."""
    index: str = ""
    text: str = ""
    resource_id: str = ""
    class_name: str = ""
    package: str = ""
    content_desc: str = ""
    checkable: bool = False
    checked: bool = False
    clickable: bool = False
    enabled: bool = True
    focusable: bool = False
    focused: bool = False
    scrollable: bool = False
    long_clickable: bool = False
    password: bool = False
    selected: bool = False
    bounds: str = "[0,0][0,0]"
    bounds_coords: tuple = (0, 0, 0, 0)  # (left, top, right, bottom)
    center_x: int = 0
    center_y: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "text": self.text,
            "resource_id": self.resource_id,
            "class_name": self.class_name,
            "package": self.package,
            "content_desc": self.content_desc,
            "clickable": self.clickable,
            "bounds": self.bounds,
            "center": [self.center_x, self.center_y],
        }


@dataclass
class MissionStep:
    """Definición de un paso dentro de una misión."""
    action: str
    step_id: Optional[str] = None
    target: Optional[Any] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    wait_for: Optional[Any] = None
    expected_state: Optional[Dict[str, Any]] = None
    timeout: float = 15.0
    retry: int = 2
    security_level: Optional[str] = None
    on_failure: str = "ABORT"  # "ABORT" o "CONTINUE"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "target": self.target,
            "parameters": self.parameters,
            "wait_for": self.wait_for,
            "expected_state": self.expected_state,
            "timeout": self.timeout,
            "retry": self.retry,
            "security_level": self.security_level,
            "on_failure": self.on_failure,
        }


@dataclass
class StepResult:
    """Resultado detallado de la ejecución de un paso de misión."""
    step_id: str
    action: str
    target: Any
    success: bool
    verification_passed: bool
    details: str = ""
    duration_s: float = 0.0
    screenshot_path: Optional[str] = None
    ui_xml_path: Optional[str] = None
    error_message: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "step_id": self.step_id,
            "action": self.action,
            "target": self.target,
            "success": self.success,
            "verification_passed": self.verification_passed,
            "details": self.details,
            "duration_s": round(self.duration_s, 3),
            "screenshot_path": self.screenshot_path,
            "ui_xml_path": self.ui_xml_path,
            "error_message": self.error_message,
        }


@dataclass
class Mission:
    """Definición formal de una misión de automatización Android."""
    name: str
    device: str = "HermesPhone"
    timeout: float = 300.0
    steps: List[MissionStep] = field(default_factory=list)
    description: str = ""
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "device": self.device,
            "timeout": self.timeout,
            "description": self.description,
            "created_at": self.created_at,
            "steps": [s.to_dict() for s in self.steps],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Mission":
        steps_raw = data.get("steps", [])
        steps = []
        for idx, s in enumerate(steps_raw, 1):
            if isinstance(s, dict):
                step_id = s.get("step_id", f"STEP_{idx:02d}")
                steps.append(
                    MissionStep(
                        action=s.get("action", ""),
                        step_id=step_id,
                        target=s.get("target"),
                        parameters=s.get("parameters", {}),
                        wait_for=s.get("wait_for"),
                        expected_state=s.get("expected_state"),
                        timeout=float(s.get("timeout", 15.0)),
                        retry=int(s.get("retry", 2)),
                        security_level=s.get("security_level"),
                        on_failure=s.get("on_failure", "ABORT"),
                    )
                )
        return cls(
            name=data.get("name", "Unnamed_Mission"),
            device=data.get("device", "HermesPhone"),
            timeout=float(data.get("timeout", 300.0)),
            description=data.get("description", ""),
            steps=steps,
        )


@dataclass
class MissionReport:
    """Informe de ejecución y auditoría de una misión."""
    mission_name: str
    device: str
    success: bool
    total_steps: int
    successful_steps: int
    failed_steps: int
    duration_s: float
    evidence_dir: str
    steps_results: List[StepResult] = field(default_factory=list)
    error_summary: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mission_name": self.mission_name,
            "device": self.device,
            "success": self.success,
            "total_steps": self.total_steps,
            "successful_steps": self.successful_steps,
            "failed_steps": self.failed_steps,
            "duration_s": round(self.duration_s, 3),
            "evidence_dir": self.evidence_dir,
            "error_summary": self.error_summary,
            "steps_results": [r.to_dict() for r in self.steps_results],
        }
