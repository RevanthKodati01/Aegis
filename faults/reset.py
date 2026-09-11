"""
reset.py
--------
Restore the warehouse to a clean state by regenerating bronze data and
rebuilding the dbt models. Use this between fault demos.
"""

import subprocess
import sys


def reset_warehouse():
    print("Regenerating clean bronze data...")
    subprocess.run([sys.executable, "warehouse/generate_data.py"], check=True)
    print("Rebuilding dbt models...")
    subprocess.run(
        ["dbt", "run"],
        cwd="dbt_project",
        env={**__import__("os").environ, "DBT_PROFILES_DIR": "."},
        check=True,
    )
    print("Warehouse reset to clean state.")


if __name__ == "__main__":
    reset_warehouse()