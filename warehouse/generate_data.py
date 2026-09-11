"""
generate_data.py
----------------
Generates realistic synthetic data for the Aegis warehouse and loads it
into the bronze tables (raw_users, raw_subscriptions, raw_events).

Design goals:
- Users spread across 90 days, countries, and acquisition channels.
- Subscriptions: only some users convert; some later churn.
- Events: follow a funnel (many views, few purchases) AND a daily rhythm
  (busy midday, quiet at night, lighter weekends).
- Reproducible: a fixed seed means the same data every run.
"""

import duckdb
import random
import json
import uuid
from datetime import datetime, timedelta, date

from faker import Faker

# ----------------------------------------------------------------------
# CONFIG - the "knobs" for our data. Change these to scale up/down.
# ----------------------------------------------------------------------
DB_PATH = "aegis.duckdb"
SEED = 42                     # fixed seed -> reproducible data
NUM_USERS = 2000              # how many users to create
NUM_DAYS = 90                 # how many days of history
END_DATE = date(2026, 6, 30)  # the last day in our window
START_DATE = END_DATE - timedelta(days=NUM_DAYS - 1)

COUNTRIES = ["US", "UK", "IN", "DE", "CA", "AU", "FR", "BR"]
CHANNELS = ["organic", "paid_ads", "referral", "social", "email"]
PLAN_TIERS = ["pro", "enterprise"]          # paid tiers (free users have no subscription row)
PLAN_MRR = {"pro": 49.00, "enterprise": 299.00}

# Event funnel: relative weights. page_view is most common, purchase rarest.
EVENT_FUNNEL = {
    "page_view":       60,
    "sign_up":         10,
    "feature_used":    20,
    "checkout_started": 6,
    "purchase":         4,
}

SOURCES = ["web", "ios", "android"]

# Set the seeds so every run is identical.
random.seed(SEED)
fake = Faker()
Faker.seed(SEED)


# ----------------------------------------------------------------------
# 1. USERS
# ----------------------------------------------------------------------
def generate_users():
    """Return a list of user dicts, each signing up on a random day."""
    users = []
    for _ in range(NUM_USERS):
        signup_offset = random.randint(0, NUM_DAYS - 1)   # which day they signed up
        signup = START_DATE + timedelta(days=signup_offset)
        users.append({
            "user_id": str(uuid.uuid4()),      # a unique id
            "signup_date": signup,
            "country": random.choice(COUNTRIES),
            "acquisition_channel": random.choice(CHANNELS),
            "is_active": random.random() < 0.85,  # ~85% still active
        })
    return users


# ----------------------------------------------------------------------
# 2. SUBSCRIPTIONS
# ----------------------------------------------------------------------
def generate_subscriptions(users):
    """~20% of users convert to a paid plan; some of those later churn."""
    subs = []
    for u in users:
        if random.random() < 0.20:            # 20% conversion to paid
            tier = random.choice(PLAN_TIERS)
            started = u["signup_date"] + timedelta(days=random.randint(0, 10))
            # ~25% of paid users churn at some later point
            canceled = None
            status = "active"
            if random.random() < 0.25:
                churn_days = random.randint(15, 80)
                candidate = started + timedelta(days=churn_days)
                if candidate <= END_DATE:
                    canceled = candidate
                    status = "canceled"
            subs.append({
                "subscription_id": str(uuid.uuid4()),
                "user_id": u["user_id"],
                "plan_tier": tier,
                "mrr_amount": PLAN_MRR[tier],
                "currency": "USD",
                "status": status,
                "started_at": started,
                "canceled_at": canceled,
            })
    return subs


# ----------------------------------------------------------------------
# 3. EVENTS  (the firehose - funnel + daily rhythm)
# ----------------------------------------------------------------------
def hour_weight(hour):
    """Return a relative activity weight for a given hour (0-23).
    Peaks around midday, low overnight. Rough bell shape."""
    # distance from 1pm (13:00), the peak
    distance = abs(hour - 13)
    return max(1, 12 - distance)   # 12 at peak, tapering to 1

def generate_events(users):
    """Generate events per user per active day, following funnel + rhythm."""
    events = []
    event_types = list(EVENT_FUNNEL.keys())
    weights = list(EVENT_FUNNEL.values())

    for u in users:
        # A user is 'active' on a random subset of days after signup.
        active_from = u["signup_date"]
        possible_days = (END_DATE - active_from).days
        if possible_days <= 0:
            continue
        # how many days this user shows up (engagement varies a lot)
        num_active_days = random.randint(1, max(1, possible_days // 2))
        active_days = random.sample(range(possible_days + 1),
                                    min(num_active_days, possible_days + 1))

        for day_offset in active_days:
            current_day = active_from + timedelta(days=day_offset)
            # weekends are lighter
            is_weekend = current_day.weekday() >= 5
            base_events = random.randint(1, 8)
            if is_weekend:
                base_events = max(1, base_events // 2)

            for _ in range(base_events):
                etype = random.choices(event_types, weights=weights, k=1)[0]
                # pick an hour weighted toward midday
                hours = list(range(24))
                hweights = [hour_weight(h) for h in hours]
                hour = random.choices(hours, weights=hweights, k=1)[0]
                minute = random.randint(0, 59)
                ts = datetime.combine(current_day, datetime.min.time()) + \
                     timedelta(hours=hour, minutes=minute)

                # 'properties' is extra data stored as a JSON string
                props = json.dumps({
                    "page": random.choice(["/home", "/pricing", "/docs", "/app"]),
                    "device": random.choice(["desktop", "mobile", "tablet"]),
                })

                events.append({
                    "event_id": str(uuid.uuid4()),
                    "user_id": u["user_id"],
                    "event_type": etype,
                    "ts": ts,
                    "properties": props,
                    "source": random.choice(SOURCES),
                })
    return events


# ----------------------------------------------------------------------
# LOAD into DuckDB
# ----------------------------------------------------------------------
def load(con, table, rows, columns):
    """Insert a list of dicts into a DuckDB table."""
    if not rows:
        print(f"  (no rows for {table})")
        return
    # Build a list of tuples in column order.
    data = [tuple(r[c] for c in columns) for r in rows]
    placeholders = ", ".join(["?"] * len(columns))
    con.executemany(
        f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})",
        data,
    )
    print(f"  loaded {len(rows):,} rows into {table}")


def main():
    con = duckdb.connect(DB_PATH)

    # Clear any existing data so re-runs start clean (idempotent load).
    for t in ["raw_events", "raw_subscriptions", "raw_users"]:
        con.execute(f"DELETE FROM {t};")

    print("Generating users...")
    users = generate_users()
    print("Generating subscriptions...")
    subs = generate_subscriptions(users)
    print("Generating events...")
    events = generate_events(users)

    print("Loading into warehouse...")
    load(con, "raw_users", users,
         ["user_id", "signup_date", "country", "acquisition_channel", "is_active"])
    load(con, "raw_subscriptions", subs,
         ["subscription_id", "user_id", "plan_tier", "mrr_amount",
          "currency", "status", "started_at", "canceled_at"])
    load(con, "raw_events", events,
         ["event_id", "user_id", "event_type", "ts", "properties", "source"])

    # Quick sanity summary.
    print("\nSummary:")
    for t in ["raw_users", "raw_subscriptions", "raw_events"]:
        count = con.execute(f"SELECT COUNT(*) FROM {t};").fetchone()[0]
        print(f"  {t}: {count:,} rows")

    con.close()
    print("\nDone.")


if __name__ == "__main__":
    main()