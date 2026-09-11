"""
faults_catalog.py
-----------------
The catalog of injectable faults. Each function breaks the warehouse in a
realistic way and returns a FaultResult with a LABELED ground-truth root cause.

IMPORTANT: faults mutate the BRONZE (raw_) tables, because that is where real
breaks originate. Downstream silver/gold and the contracts then reflect the
damage - exactly the upstream->downstream propagation the Diagnostician traces.
"""

import duckdb
from faults.fault_result import FaultResult

DB_PATH = "aegis.duckdb"


def _connect(db_path):
    return duckdb.connect(db_path)


def inject_schema_drift(db_path=DB_PATH):
    """
    Schema drift: an upstream change makes mrr_amount arrive corrupted so
    a chunk of values become NULL. Simulates 'amount now arrives as text and
    the cast silently nulls it'. Breaks revenue (MRR).
    """
    con = _connect(db_path)
    # Null out mrr_amount for ~40% of subscriptions (simulate failed casts).
    rows = con.execute("""
        UPDATE raw_subscriptions
        SET mrr_amount = NULL
        WHERE subscription_id IN (
            SELECT subscription_id FROM raw_subscriptions
            USING SAMPLE 40 PERCENT (bernoulli)
        )
    """).fetchall()
    affected = con.execute(
        "SELECT COUNT(*) FROM raw_subscriptions WHERE mrr_amount IS NULL"
    ).fetchone()[0]
    con.close()
    return FaultResult(
        fault_name="schema_drift",
        description="mrr_amount corrupted to NULL for a subset of subscriptions",
        affected_table="raw_subscriptions",
        affected_column="mrr_amount",
        ground_truth_root_cause=(
            "Upstream type change on raw_subscriptions.mrr_amount caused values "
            "to fail casting to decimal, landing as NULL. Propagates to fct_subscriptions "
            "and collapses the mrr gold metric."
        ),
        expected_symptom="MRR drops sharply; not_null check on mrr_amount fails",
        rows_affected=affected,
    )


def inject_duplicate_events(db_path=DB_PATH):
    """
    Duplicate events: a batch is re-ingested, so event_ids repeat.
    Breaks uniqueness and inflates DAU (duplicates look like activity).
    """
    con = _connect(db_path)
    before = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    # Re-insert ~10% of events verbatim (same event_ids -> duplicates).
    con.execute("""
        INSERT INTO raw_events
        SELECT * FROM raw_events USING SAMPLE 10 PERCENT (bernoulli)
    """)
    after = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    con.close()
    return FaultResult(
        fault_name="duplicate_events",
        description="A batch of events was re-ingested, duplicating event_ids",
        affected_table="raw_events",
        affected_column="event_id",
        ground_truth_root_cause=(
            "A pipeline re-ran and re-ingested an event batch without dedup, "
            "creating duplicate event_ids. Inflates distinct-activity-based metrics "
            "like DAU and violates event_id uniqueness."
        ),
        expected_symptom="event_id uniqueness fails; DAU inflated; row count jumps",
        rows_affected=after - before,
    )


def inject_null_spike(db_path=DB_PATH):
    """
    Null spike: a source mapping change nulls out country for a chunk of users.
    Breaks the null_rate / not_null distribution contracts.
    """
    con = _connect(db_path)
    con.execute("""
        UPDATE raw_users
        SET country = NULL
        WHERE user_id IN (
            SELECT user_id FROM raw_users USING SAMPLE 15 PERCENT (bernoulli)
        )
    """)
    affected = con.execute(
        "SELECT COUNT(*) FROM raw_users WHERE country IS NULL"
    ).fetchone()[0]
    con.close()
    return FaultResult(
        fault_name="null_spike",
        description="country nulled out for a subset of users",
        affected_table="raw_users",
        affected_column="country",
        ground_truth_root_cause=(
            "An upstream source-mapping change stopped populating raw_users.country "
            "for a segment of users, producing a spike in NULLs."
        ),
        expected_symptom="null_rate/not_null checks on country fail",
        rows_affected=affected,
    )


def inject_volume_drop(db_path=DB_PATH):
    """
    Volume drop: a partial batch failure deletes a large slice of recent events.
    Breaks the row_count / volume contract and craters DAU.
    """
    con = _connect(db_path)
    before = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    # Delete ~40% of events (simulate a dropped batch).
    con.execute("""
        DELETE FROM raw_events
        WHERE event_id IN (
            SELECT event_id FROM raw_events USING SAMPLE 40 PERCENT (bernoulli)
        )
    """)
    after = con.execute("SELECT COUNT(*) FROM raw_events").fetchone()[0]
    con.close()
    return FaultResult(
        fault_name="volume_drop",
        description="A large slice of events was deleted (dropped batch)",
        affected_table="raw_events",
        affected_column=None,
        ground_truth_root_cause=(
            "A partial pipeline batch failure dropped a large portion of event rows, "
            "reducing volume and depressing activity metrics like DAU."
        ),
        expected_symptom="row_count/volume check trends low; DAU craters",
        rows_affected=before - after,
    )


# Registry: maps fault name -> function. The CLI and eval use this.
FAULT_CATALOG = {
    "schema_drift": inject_schema_drift,
    "duplicate_events": inject_duplicate_events,
    "null_spike": inject_null_spike,
    "volume_drop": inject_volume_drop,
}