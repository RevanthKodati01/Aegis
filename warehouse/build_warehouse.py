"""
build_warehouse.py
------------------
Creates the Aegis DuckDB warehouse and the bronze-layer raw tables.
Bronze = raw data as ingested. We define the tables here (empty);
data gets generated in the next stage.
"""

import duckdb  # the library that lets Python talk to DuckDB

# The database is a single file on disk. If it doesn't exist, DuckDB
# creates it. We put it at the project root so everything can find it.
DB_PATH = "aegis.duckdb"


def build_bronze_tables(con):
    """Create the three bronze (raw) tables if they don't already exist."""

    # --- raw_events: the behavioral firehose (clicks, signups, purchases) ---
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_events (
            event_id    VARCHAR,     -- unique id for each event
            user_id     VARCHAR,     -- which user did it
            event_type  VARCHAR,     -- 'page_view', 'sign_up', 'purchase', etc.
            ts          TIMESTAMP,   -- when it happened
            properties  VARCHAR,     -- extra data as a JSON string
            source      VARCHAR      -- where the event came from (web, ios, ...)
        );
    """)

    # --- raw_users: the user dimension (one row per user) ---
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_users (
            user_id             VARCHAR,   -- unique id
            signup_date         DATE,      -- when they signed up
            country             VARCHAR,   -- their country
            acquisition_channel VARCHAR,   -- how we acquired them (ads, organic...)
            is_active           BOOLEAN    -- currently active?
        );
    """)

    # --- raw_subscriptions: the monetization source (feeds MRR/churn) ---
    con.execute("""
        CREATE TABLE IF NOT EXISTS raw_subscriptions (
            subscription_id VARCHAR,     -- unique id
            user_id         VARCHAR,     -- which user owns it
            plan_tier       VARCHAR,     -- 'free', 'pro', 'enterprise'
            mrr_amount      DECIMAL(10,2),  -- monthly recurring revenue, money type
            currency        VARCHAR,     -- 'USD', 'EUR', etc.
            status          VARCHAR,     -- 'active', 'canceled'
            started_at      DATE,        -- when the subscription began
            canceled_at     DATE         -- when it was canceled (null if active)
        );
    """)


def main():
    # Connect to (or create) the database file.
    con = duckdb.connect(DB_PATH)
    print(f"Connected to warehouse at: {DB_PATH}")

    # Build the bronze tables.
    build_bronze_tables(con)
    print("Bronze tables created: raw_events, raw_users, raw_subscriptions")

    # Show the tables that now exist, as a sanity check.
    tables = con.execute("SHOW TABLES;").fetchall()
    print("Tables in warehouse:", [t[0] for t in tables])

    # Always close the connection when done.
    con.close()
    print("Done.")


# This runs main() only when you execute the file directly.
if __name__ == "__main__":
    main()