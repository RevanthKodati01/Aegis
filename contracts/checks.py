"""
checks.py
---------
The check functions. Each runs SQL against DuckDB and returns a CheckResult.
All checks share the same signature so the runner can call them uniformly.
"""

from datetime import datetime, date
from contracts.check_result import CheckResult


def check_row_count(con, table, spec):
    """Volume check: table must have at least min_rows rows."""
    min_rows = spec["min_rows"]
    observed = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    passed = observed >= min_rows
    return CheckResult(
        table=table, check_type="row_count", column=None,
        passed=passed, observed=observed, expected=f">= {min_rows}",
        severity=spec["severity"],
        message=(f"row count {observed:,} meets minimum {min_rows:,}" if passed
                 else f"row count {observed:,} BELOW minimum {min_rows:,}"),
    )


def check_not_null(con, table, spec):
    """Not-null check: a column must have zero nulls."""
    col = spec["column"]
    nulls = con.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL"
    ).fetchone()[0]
    passed = nulls == 0
    return CheckResult(
        table=table, check_type="not_null", column=col,
        passed=passed, observed=nulls, expected=0,
        severity=spec["severity"],
        message=(f"no nulls in {col}" if passed
                 else f"{nulls:,} nulls found in {col}"),
    )


def check_null_rate(con, table, spec):
    """Null-rate check: fraction of nulls must be under max_null_rate."""
    col = spec["column"]
    max_rate = spec["max_null_rate"]
    total = con.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
    nulls = con.execute(
        f"SELECT COUNT(*) FROM {table} WHERE {col} IS NULL"
    ).fetchone()[0]
    rate = (nulls / total) if total else 0
    passed = rate <= max_rate
    return CheckResult(
        table=table, check_type="null_rate", column=col,
        passed=passed, observed=round(rate, 4), expected=f"<= {max_rate}",
        severity=spec["severity"],
        message=(f"null rate {rate:.2%} within limit {max_rate:.0%}" if passed
                 else f"null rate {rate:.2%} EXCEEDS limit {max_rate:.0%}"),
    )


def check_uniqueness(con, table, spec):
    """Uniqueness check: a column must have no duplicate values."""
    col = spec["column"]
    dupes = con.execute(f"""
        SELECT COUNT(*) FROM (
            SELECT {col} FROM {table}
            GROUP BY {col} HAVING COUNT(*) > 1
        )
    """).fetchone()[0]
    passed = dupes == 0
    return CheckResult(
        table=table, check_type="uniqueness", column=col,
        passed=passed, observed=dupes, expected=0,
        severity=spec["severity"],
        message=(f"{col} is unique" if passed
                 else f"{dupes:,} duplicate {col} values found"),
    )


def check_freshness(con, table, spec):
    """Freshness check: newest timestamp must be within max_age_days of today."""
    col = spec["column"]
    max_age = spec["max_age_days"]
    latest = con.execute(f"SELECT MAX({col}) FROM {table}").fetchone()[0]
    if latest is None:
        passed, age_days = False, None
        msg = f"no timestamps found in {col}"
    else:
        if isinstance(latest, datetime):
            latest_date = latest.date()
        elif isinstance(latest, date):
            latest_date = latest
        else:
            latest_date = datetime.fromisoformat(str(latest)).date()
        age_days = (date.today() - latest_date).days
        passed = age_days <= max_age
        msg = (f"data is {age_days} days old, within {max_age}" if passed
               else f"data is {age_days} days old, EXCEEDS {max_age}")
    return CheckResult(
        table=table, check_type="freshness", column=col,
        passed=passed, observed=age_days, expected=f"<= {max_age} days",
        severity=spec["severity"], message=msg,
    )


def check_accepted_values(con, table, spec):
    """Accepted-values check: a column must only contain allowed values."""
    col = spec["column"]
    allowed = spec["allowed"]
    # Build a quoted list for SQL, e.g. 'active','canceled'
    allowed_sql = ", ".join(f"'{v}'" for v in allowed)
    bad = con.execute(f"""
        SELECT COUNT(*) FROM {table}
        WHERE {col} IS NOT NULL AND {col} NOT IN ({allowed_sql})
    """).fetchone()[0]
    passed = bad == 0
    return CheckResult(
        table=table, check_type="accepted_values", column=col,
        passed=passed, observed=bad, expected=f"in {allowed}",
        severity=spec["severity"],
        message=(f"all {col} values allowed" if passed
                 else f"{bad:,} rows have disallowed {col} values"),
    )


# A dispatch table: maps a check "type" from the YAML to its function.
CHECK_DISPATCH = {
    "row_count": check_row_count,
    "not_null": check_not_null,
    "null_rate": check_null_rate,
    "uniqueness": check_uniqueness,
    "freshness": check_freshness,
    "accepted_values": check_accepted_values,
}