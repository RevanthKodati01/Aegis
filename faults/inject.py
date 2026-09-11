"""
inject.py
---------
Command-line entry point for injecting faults.

Usage:
    python -m faults.inject <fault_name>
    python -m faults.inject --list
"""

import sys
from faults.faults_catalog import FAULT_CATALOG


def main():
    args = sys.argv[1:]

    if not args or args[0] in ("--list", "-l"):
        print("Available faults:")
        for name in FAULT_CATALOG:
            print(f"  - {name}")
        print("\nUsage: python -m faults.inject <fault_name>")
        return

    fault_name = args[0]
    func = FAULT_CATALOG.get(fault_name)
    if func is None:
        print(f"Unknown fault: {fault_name}")
        print(f"Available: {', '.join(FAULT_CATALOG)}")
        sys.exit(1)

    print(f"Injecting fault: {fault_name}...\n")
    result = func()
    print(result)
    print("\nFault injected. Run the contract checker to see it detected:")
    print("  python3 -m contracts.runner")


if __name__ == "__main__":
    main()
