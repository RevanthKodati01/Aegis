"""
check_result.py
---------------
The standard structured result every contract check returns.
The Monitor agent turns failing CheckResults into incidents, so this
shape is the contract between the detection layer and the agents.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Optional


# A dataclass is a lightweight Python class for holding structured data.
# It auto-generates the __init__, so we just declare the fields.
@dataclass
class CheckResult:
    table: str                      # which table was checked, e.g. "raw_events"
    check_type: str                 # e.g. "null_rate", "freshness", "uniqueness"
    column: Optional[str]           # which column (None for table-level checks)
    passed: bool                    # did the check pass?
    observed: Any                   # what we actually measured (e.g. 0.34)
    expected: Any                   # what the contract expected (e.g. "< 0.02")
    severity: str                   # "low" | "medium" | "high" | "critical"
    message: str                    # human-readable summary of the result
    context: dict = field(default_factory=dict)  # any extra detail for the agents

    def to_dict(self):
        """Convert to a plain dict (useful for JSON, logging, passing to agents)."""
        return asdict(self)

    def __str__(self):
        status = "PASS" if self.passed else "FAIL"
        col = f".{self.column}" if self.column else ""
        return f"[{status}] {self.table}{col} ({self.check_type}): {self.message}"