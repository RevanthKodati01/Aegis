"""
fault_result.py
---------------
Structured description of an injected fault, including its LABELED
ground-truth root cause. This label is the answer key used later to
grade the Diagnostician agent, so it must describe the true root cause
precisely (table, column, and what actually went wrong).
"""

from dataclasses import dataclass, field, asdict
from typing import Optional


@dataclass
class FaultResult:
    fault_name: str              # e.g. "schema_drift"
    description: str             # human summary of what was injected
    affected_table: str          # where the break was applied
    affected_column: Optional[str]
    ground_truth_root_cause: str  # the ANSWER KEY - true root cause
    expected_symptom: str        # what a monitor/metric should show
    rows_affected: int           # how many rows were changed
    context: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

    def __str__(self):
        return (f"[FAULT: {self.fault_name}] {self.description}\n"
                f"  root cause: {self.ground_truth_root_cause}\n"
                f"  expected symptom: {self.expected_symptom}\n"
                f"  rows affected: {self.rows_affected}")