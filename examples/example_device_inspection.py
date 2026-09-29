"""
Example: Inspect connected Android devices and capture screen state with HermesAndroidAgent.
"""

import os
import sys

# Add python directory to sys.path
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "python"))

from hermes_android import HermesAndroidAgent


def main():
    print("[*] Initializing HermesAndroidAgent...")
    agent = HermesAndroidAgent()
    
    print("\n[+] Discovering Android Devices:")
    devices = agent.list_devices()
    for dev in devices:
        print(f"    - Name: {dev.get('name'):20s} | Type: {dev.get('device_type'):22s} | State: {dev.get('state')}")
    
    print("\n[+] Security Policy Check:")
    safe_ok, _, _ = agent.security_policy.check_action("screenshot")
    dest_ok, _, _ = agent.security_policy.check_action("factory_reset")
    print(f"    - 'screenshot' allowed:    {safe_ok}")
    print(f"    - 'factory_reset' allowed: {dest_ok}")


if __name__ == "__main__":
    main()
