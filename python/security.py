"""
Módulo de Seguridad Operacional para Hermes Android.
Define la clasificación de seguridad de acciones y la política de ejecución.
"""

from enum import Enum
from typing import Dict, Any, Tuple


class SecurityLevel(str, Enum):
    SAFE = "SAFE"
    REVERSIBLE = "REVERSIBLE"
    SENSITIVE = "SENSITIVE"
    DESTRUCTIVE = "DESTRUCTIVE"


# Clasificación por defecto de acciones
ACTION_SECURITY_MAP: Dict[str, SecurityLevel] = {
    # SAFE (Solo lectura e inspección)
    "screenshot": SecurityLevel.SAFE,
    "get_foreground_app": SecurityLevel.SAFE,
    "get_ui_tree": SecurityLevel.SAFE,
    "find_element": SecurityLevel.SAFE,
    "get_package_info": SecurityLevel.SAFE,
    "is_app_installed": SecurityLevel.SAFE,
    "device_status": SecurityLevel.SAFE,
    "list_devices": SecurityLevel.SAFE,
    "wait_for": SecurityLevel.SAFE,
    "verify": SecurityLevel.SAFE,
    "status": SecurityLevel.SAFE,
    
    # REVERSIBLE (Interacciones estándar de navegación y ciclo de vida seguro)
    "tap": SecurityLevel.REVERSIBLE,
    "tap_element": SecurityLevel.REVERSIBLE,
    "swipe": SecurityLevel.REVERSIBLE,
    "type": SecurityLevel.REVERSIBLE,
    "press": SecurityLevel.REVERSIBLE,
    "open_app": SecurityLevel.REVERSIBLE,
    "launch_app": SecurityLevel.REVERSIBLE,
    "close_app": SecurityLevel.REVERSIBLE,
    "home": SecurityLevel.REVERSIBLE,
    "back": SecurityLevel.REVERSIBLE,
    "start_device": SecurityLevel.REVERSIBLE,
    "stop_device": SecurityLevel.REVERSIBLE,
    "wait_for_boot": SecurityLevel.REVERSIBLE,
    
    # SENSITIVE (Acciones que tocan datos, cuentas o comunicaciones)
    "send_message": SecurityLevel.SENSITIVE,
    "account_login": SecurityLevel.SENSITIVE,
    "grant_permission": SecurityLevel.SENSITIVE,
    "share_location": SecurityLevel.SENSITIVE,
    "read_contacts": SecurityLevel.SENSITIVE,
    "input_credentials": SecurityLevel.SENSITIVE,
    
    # DESTRUCTIVE (Acciones irreversibles o de borrado de datos)
    "uninstall_app": SecurityLevel.DESTRUCTIVE,
    "clear_app_data": SecurityLevel.DESTRUCTIVE,
    "delete_file": SecurityLevel.DESTRUCTIVE,
    "factory_reset": SecurityLevel.DESTRUCTIVE,
    "wipe_data": SecurityLevel.DESTRUCTIVE,
    "modify_system": SecurityLevel.DESTRUCTIVE
}


class SecurityPolicy:
    """Política de control de seguridad para ejecución de acciones y misiones."""
    
    def __init__(self, allow_sensitive: bool = False, allow_destructive: bool = False):
        self.allow_sensitive = allow_sensitive
        self.allow_destructive = allow_destructive

    def check_action(self, action_name: str, target: Any = None) -> Tuple[bool, SecurityLevel, str]:
        """
        Evalúa si una acción está permitida bajo la política actual.
        Retorna (permitido, nivel_seguridad, motivo).
        """
        level = ACTION_SECURITY_MAP.get(action_name.lower(), SecurityLevel.REVERSIBLE)
        
        # Comprobación de casos específicos según target
        if action_name.lower() in ("type", "input") and target and any(w in str(target).lower() for w in ["password", "pin", "token", "cvv"]):
            level = SecurityLevel.SENSITIVE

        if level == SecurityLevel.SAFE:
            return True, level, "Acción SAFE permitida automáticamente."
        
        if level == SecurityLevel.REVERSIBLE:
            return True, level, "Acción REVERSIBLE permitida automáticamente."
        
        if level == SecurityLevel.SENSITIVE:
            if self.allow_sensitive:
                return True, level, "Acción SENSITIVE permitida por configuración explícita."
            return False, level, "Acción SENSITIVE bloqueada: requiere autorización explícita."
        
        if level == SecurityLevel.DESTRUCTIVE:
            if self.allow_destructive:
                return True, level, "Acción DESTRUCTIVE permitida por configuración explícita."
            return False, level, "Acción DESTRUCTIVE bloqueada: requiere confirmación de seguridad de alto nivel."

        return False, level, f"Nivel de seguridad desconocido: {level}"
