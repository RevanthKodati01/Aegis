"""
runner.py
---------
Loads contracts.yml, runs every check against the DuckDB warehouse,
and returns a list of CheckResults. This is what the Monitor agent calls.
"""

import yaml
import duckdb
from contracts.checks import CHECK_DISPATCH

DB_PATH = "aegis.duckdb"
CONTRACTS_PATH = "contracts/contracts.yml"


def load_contracts(path=CONTRACTS_PATH):
    """Read the YAML contract definitions into Python."""
    with open(path) as f:
        return yaml.safe_load(f)["contracts"]


def run_contracts(db_path=DB_PATH, contracts_path=CONTRACTS_PATH):
    """Run all checks defined in the contracts file. Returns list[CheckResult]."""
    con = duckdb.connect(db_path)
    contracts = load_contracts(contracts_path)
    results = []

    for contract in contracts:
        table = contract["table"]
        for spec in contract["checks"]:
            check_type = spec["type"]
            func = CHECK_DISPATCH.get(check_type)
            if func is None:
                print(f"  (unknown check type: {check_type}, skipping)")
                continue
            result = func(con, table, spec)
            results.append(result)

    con.close()
    return results


def main():
    """Run contracts and print a readable report."""
    results = run_contracts()
    passed = [r for r in results if r.passed]
    failed = [r for r in results if not r.passed]

    print(f"\nContract check report: {len(passed)} passed, {len(failed)} failed\n")
    for r in results:
        print(" ", r)

    if failed:
        print(f"\n{len(failed)} FAILING checks (by severity):")
        for r in sorted(failed, key=lambda x: x.severity):
            print(f"  [{r.severity.upper()}] {r.table}.{r.column}: {r.message}")
    else:
        print("\nAll contracts satisfied. Warehouse is healthy.")


if __name__ == "__main__":
    main()