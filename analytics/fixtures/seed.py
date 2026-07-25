#!/usr/bin/env python3
"""Build the fixture warehouse the reference docs describe, then prove they're true.

    python3 analytics/fixtures/seed.py          # writes analytics/fixtures/warehouse.db

Stdlib sqlite3, no dependencies, no credentials. Two jobs:

1. Give the agent something to actually query, so the eval suite runs offline and in CI.
2. **Verify the reference docs against the data.** Every claim in references/*.md that is
   a number ("the hygiene filter is worth ~5% of GMV", "attributed revenue is ~20% low",
   "user_id inflates customer counts ~1.7x") is asserted here. When a doc drifts from the
   warehouse, this fails — which is the rot the whole system exists to catch.

The data is small and fake. The *shape* is the point: every gotcha in the docs is present
in the rows, so an agent that ignores one gets a visibly wrong number.
"""

import random
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

DB = Path(__file__).resolve().parent / "warehouse.db"
START = date(2026, 1, 1)
DAYS = 180  # through 2026-06-29
CHANNELS = ["web", "ios", "and"]

SCHEMA = """
DROP TABLE IF EXISTS fact_orders;
DROP TABLE IF EXISTS fact_order_items;
DROP TABLE IF EXISTS dim_customer;
DROP TABLE IF EXISTS orders_v1;
DROP TABLE IF EXISTS fact_marketing_spend;
DROP TABLE IF EXISTS fact_attributed_revenue;
DROP TABLE IF EXISTS dim_marketing_touch;

CREATE TABLE dim_customer (      -- GRAIN: one row per USER, not per account
  user_id INTEGER PRIMARY KEY,
  customer_id INTEGER,           -- repeats: a B2B account has several users
  customer_email TEXT,           -- RESTRICTED: return the SQL, never the result set
  first_order_date TEXT,
  customer_segment TEXT,         -- 'b2b' | 'b2c'
  is_free_email_domain INTEGER,
  is_internal INTEGER
);
CREATE TABLE fact_orders (
  order_id INTEGER PRIMARY KEY,
  customer_id INTEGER,
  order_date TEXT,               -- America/Sao_Paulo, reporting date
  created_at TEXT,               -- UTC
  channel_code TEXT,             -- 'web'|'ios'|'and'; marketing uses channel_name
  country_iso2 TEXT,
  order_status TEXT,             -- 'completed'|'cancelled'|'fraud_blocked'
  is_test INTEGER,
  gross_merchandise_value_brl REAL,
  net_revenue_brl REAL,          -- ALREADY refund-adjusted; do not subtract refunds again
  net_revenue_usd REAL,          -- month-end FX, not order-date FX
  is_refunded INTEGER
);
CREATE TABLE fact_order_items (
  order_item_id INTEGER PRIMARY KEY,
  order_id INTEGER,
  category TEXT,
  item_revenue_brl REAL          -- excludes shipping: will not sum to order revenue
);
CREATE TABLE orders_v1 (         -- DEPRECATED, frozen 2023-06, ISO-3 country codes
  order_id INTEGER PRIMARY KEY, order_date TEXT, country_iso3 TEXT, revenue_brl REAL
);
CREATE TABLE fact_marketing_spend (
  campaign_id INTEGER, spend_date TEXT, platform TEXT, channel_name TEXT,
  is_test_campaign INTEGER, spend_usd REAL   -- negative rows are platform credits
);
CREATE TABLE fact_attributed_revenue (
  order_id INTEGER, attribution_model TEXT,  -- one row PER MODEL: 3x if not filtered
  channel_name TEXT, attributed_revenue_brl REAL
);
CREATE TABLE dim_marketing_touch (
  touch_id INTEGER PRIMARY KEY, customer_id INTEGER, order_id INTEGER,
  touch_date TEXT, channel_name TEXT         -- many per order: joining fans out revenue
);
"""

CHANNEL_NAME = {"web": "Web", "ios": "iOS", "and": "Android"}
MODELS = ["last_touch", "first_touch", "linear"]


def build(conn: sqlite3.Connection) -> None:
    rng = random.Random(20260724)  # deterministic: evals must not move between runs
    conn.executescript(SCHEMA)

    # --- customers: B2B accounts carry ~1.7 user_ids each -------------------------
    users = []
    for cid in range(1, 401):
        segment = "b2b" if cid % 3 == 0 else "b2c"
        row = (
            (START + timedelta(days=rng.randrange(DAYS))).isoformat(),
            segment,
            1 if segment == "b2c" and cid % 5 == 0 else 0,
            1 if cid % 97 == 0 else 0,
        )
        # one user per B2C account, three per B2B — the "user_id inflates ~1.7x" gotcha
        domain = "gmail.com" if row[2] else f"company{cid}.com.br"
        for seat in range(3 if segment == "b2b" else 1):
            uid = cid * 10 + seat
            users.append((uid, cid, f"user{uid}@{domain}", *row))
    conn.executemany("INSERT INTO dim_customer VALUES (?,?,?,?,?,?,?)", users)

    # --- orders --------------------------------------------------------------------
    orders, items, attributed, touches = [], [], [], []
    item_id = touch_id = 1
    for oid in range(1, 3001):
        day = START + timedelta(days=rng.randrange(DAYS))
        cid = rng.randrange(1, 401)
        gmv = round(rng.uniform(40, 900), 2)

        # ~2% test rows, ~1.5% fraud, ~1.5% cancelled → the hygiene filter has real teeth
        roll = rng.random()
        is_test = roll < 0.02
        status = (
            "fraud_blocked"
            if 0.02 <= roll < 0.035
            else "cancelled"
            if 0.035 <= roll < 0.05
            else "completed"
        )

        refunded = status == "completed" and not is_test and rng.random() < 0.06
        net = round(gmv * (0.0 if refunded else rng.uniform(0.88, 0.97)), 2)
        orders.append(
            (
                oid,
                cid,
                day.isoformat(),
                f"{day.isoformat()}T{rng.randrange(24):02d}:00:00Z",
                CHANNELS[oid % 3],
                "BR" if oid % 4 else "AR",
                status,
                int(is_test),
                gmv,
                net,
                round(net / 5.4, 2),
                int(refunded),
            )
        )

        for _ in range(rng.randrange(1, 4)):  # items exclude shipping
            items.append(
                (
                    item_id,
                    oid,
                    rng.choice(["apparel", "home", "tech", "beauty"]),
                    round(gmv * rng.uniform(0.2, 0.4), 2),
                )
            )
            item_id += 1

        # ~80% of clean orders are attributed → attributed revenue runs ~20% low
        if status == "completed" and not is_test and rng.random() < 0.82:
            chan = CHANNEL_NAME[CHANNELS[oid % 3]]
            for model in MODELS:  # one row per model
                attributed.append((oid, model, chan, net))
            for _ in range(rng.randrange(1, 5)):  # many touches per order
                touches.append((touch_id, cid, oid, day.isoformat(), chan))
                touch_id += 1

    conn.executemany("INSERT INTO fact_orders VALUES (?,?,?,?,?,?,?,?,?,?,?,?)", orders)
    conn.executemany("INSERT INTO fact_order_items VALUES (?,?,?,?)", items)
    conn.executemany("INSERT INTO fact_attributed_revenue VALUES (?,?,?,?)", attributed)
    conn.executemany("INSERT INTO dim_marketing_touch VALUES (?,?,?,?,?)", touches)

    # --- deprecated table: same-looking data, ISO-3, pre-2021 ----------------------
    conn.executemany(
        "INSERT INTO orders_v1 VALUES (?,?,?,?)",
        [
            (
                i,
                (date(2020, 1, 1) + timedelta(days=i % 365)).isoformat(),
                "BRA",
                round(rng.uniform(40, 900), 2),
            )
            for i in range(1, 501)
        ],
    )

    # --- marketing spend: negative rows are real platform credits ------------------
    spend = []
    for cmp_id in range(1, 21):
        for d in range(0, DAYS, 3):
            day = START + timedelta(days=d)
            amount = round(rng.uniform(200, 3000), 2)
            if rng.random() < 0.04:
                amount = -round(rng.uniform(50, 400), 2)  # credit
            spend.append(
                (
                    cmp_id,
                    day.isoformat(),
                    rng.choice(["google", "meta", "tiktok"]),
                    CHANNEL_NAME[CHANNELS[cmp_id % 3]],
                    int(cmp_id % 19 == 0),
                    amount,
                )
            )
    conn.executemany("INSERT INTO fact_marketing_spend VALUES (?,?,?,?,?,?)", spend)
    conn.executescript(SEMANTIC_LAYER)
    conn.commit()


HYGIENE = "is_test = 0 AND order_status NOT IN ('cancelled','fraud_blocked')"

# The semantic layer, as far as SQLite can express one: a governed view with the hygiene
# filter, the de-duplicated customer join, and the named segments already baked in. An
# agent that aggregates `sem_orders` cannot omit the fraud filter, cannot fan out on the
# per-user dim_customer, and cannot hand-roll a segment — which is the entire point.
# Measures stay additive so any window or dimension composes; ratios are computed from
# the sums, never averaged.
SEMANTIC_LAYER = f"""
DROP VIEW IF EXISTS sem_orders;
CREATE VIEW sem_orders AS
SELECT o.order_id, o.order_date, o.channel_code, o.country_iso2,
       c.customer_id, c.customer_segment,
       o.net_revenue_brl        AS net_revenue,
       o.gross_merchandise_value_brl AS gmv,
       o.net_revenue_usd        AS net_revenue_usd,
       o.is_refunded,
       -- named segments: canonical populations, not hand-rolled WHERE clauses
       CASE WHEN c.customer_segment = 'b2b' AND c.is_free_email_domain = 0
            THEN 1 ELSE 0 END   AS seg_paying_b2b,
       CASE WHEN c.first_order_date = o.order_date THEN 1 ELSE 0 END AS seg_new_customer,
       CASE WHEN c.is_internal = 0 THEN 1 ELSE 0 END AS seg_excl_internal
FROM fact_orders o
JOIN (SELECT customer_id, MIN(first_order_date) AS first_order_date,
             MAX(customer_segment) AS customer_segment,
             MAX(is_free_email_domain) AS is_free_email_domain,
             MAX(is_internal) AS is_internal
      FROM dim_customer GROUP BY customer_id) c   -- de-duplicated: dim is per-user
  ON c.customer_id = o.customer_id
WHERE o.{HYGIENE};
"""


def verify(conn: sqlite3.Connection) -> None:
    """Assert the numeric claims the reference docs make. Doc drift fails here."""
    q = lambda sql: conn.execute(sql).fetchone()[0]  # noqa: E731

    # references/orders.md: "omitting it inflates GMV by ~5%"
    dirty = q("SELECT SUM(gross_merchandise_value_brl) FROM fact_orders")
    clean = q(
        f"SELECT SUM(gross_merchandise_value_brl) FROM fact_orders WHERE {HYGIENE}"
    )
    inflation = dirty / clean - 1
    assert 0.04 <= inflation <= 0.06, (
        f"hygiene-filter inflation is {inflation:.1%}, doc says ~5%"
    )

    # references/orders.md: item revenue excludes shipping, so it must NOT match order revenue
    item_total = q("SELECT SUM(item_revenue_brl) FROM fact_order_items")
    order_total = q("SELECT SUM(net_revenue_brl) FROM fact_orders")
    assert abs(item_total / order_total - 1) > 0.05, (
        "item and order grain must disagree"
    )

    # references/metrics.md: counting user_id inflates customer counts ~1.7x
    accounts = q("SELECT COUNT(DISTINCT customer_id) FROM dim_customer")
    users = q("SELECT COUNT(DISTINCT user_id) FROM dim_customer")
    assert 1.5 <= users / accounts <= 1.9, (
        f"user/account ratio is {users / accounts:.2f}, doc says ~1.7x"
    )

    # references/marketing.md: attributed revenue is ~20% below total revenue
    total = q(f"SELECT SUM(net_revenue_brl) FROM fact_orders WHERE {HYGIENE}")
    attr = q(
        "SELECT SUM(attributed_revenue_brl) FROM fact_attributed_revenue "
        "WHERE attribution_model = 'last_touch'"
    )
    gap = 1 - attr / total
    assert 0.17 <= gap <= 0.23, f"attributed revenue is {gap:.1%} low, doc says ~20%"

    # references/marketing.md: forgetting attribution_model triples every number
    all_models = q("SELECT SUM(attributed_revenue_brl) FROM fact_attributed_revenue")
    assert abs(all_models / attr - 3) < 0.01, (
        "all-models total must be exactly 3x last_touch"
    )

    # references/marketing.md: joining touches to orders fans revenue out
    fanned = q("""SELECT SUM(o.net_revenue_brl) FROM fact_orders o
                  JOIN dim_marketing_touch t ON t.order_id = o.order_id""")
    assert fanned > total * 1.5, "touch join must visibly fan out revenue"

    # references/marketing.md: negative spend rows exist and are real credits
    assert q("SELECT COUNT(*) FROM fact_marketing_spend WHERE spend_usd < 0") > 0

    # references/orders.md: refunded orders carry net_revenue 0 — subtracting refunds
    # again would double-count
    assert (
        q(
            "SELECT COUNT(*) FROM fact_orders WHERE is_refunded = 1 AND net_revenue_brl > 0"
        )
        == 0
    )

    # references/orders.md: customer_email is restricted, and the free-email flag must
    # agree with the address — the B2B "exclude free-email domains" cut depends on it
    assert (
        q(
            "SELECT COUNT(*) FROM dim_customer WHERE customer_email LIKE '%@gmail.com'"
            " AND is_free_email_domain = 0"
        )
        == 0
    ), "free-email flag disagrees with address"

    # references/orders.md: dim_customer is per-user, so a naive join fans out B2B orders
    joined = q(f"""SELECT SUM(o.net_revenue_brl) FROM fact_orders o
                   JOIN dim_customer c ON c.customer_id = o.customer_id
                   WHERE {HYGIENE}""")
    assert joined > total * 1.4, "naive dim_customer join must visibly fan out revenue"

    # The semantic layer must return exactly the governed number — that is what makes it
    # the tier-1 answer. If these ever diverge, the view is lying and every metrics.md
    # claim goes with it.
    assert abs(q("SELECT SUM(net_revenue) FROM sem_orders") - total) < 0.01, (
        "sem_orders net_revenue must equal the governed fact_orders number"
    )
    assert q("SELECT COUNT(*) FROM sem_orders") == q(
        f"SELECT COUNT(*) FROM fact_orders WHERE {HYGIENE}"
    ), "sem_orders must not fan out on the per-user dim_customer"
    # and it must be *impossible* to get the un-hygienic number through it
    assert q("SELECT SUM(gmv) FROM sem_orders") < dirty, (
        "hygiene not baked into the view"
    )
    for seg in ("seg_paying_b2b", "seg_new_customer", "seg_excl_internal"):
        assert (
            0
            < q(f"SELECT SUM({seg}) FROM sem_orders")
            < q("SELECT COUNT(*) FROM sem_orders")
        ), f"{seg} must select a real, non-trivial subset"

    print(
        f"docs verified against data: hygiene +{inflation:.1%} · "
        f"users/accounts {users / accounts:.2f}x · attributed -{gap:.1%} · "
        f"naive customer join +{joined / total - 1:.0%} · sem_orders ✓"
    )


def main() -> int:
    DB.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB)
    try:
        build(conn)
        verify(conn)
    finally:
        conn.close()
    rows = "  ".join(
        f"{t}={sqlite3.connect(DB).execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0]}"
        for t in (
            "fact_orders",
            "fact_order_items",
            "dim_customer",
            "fact_attributed_revenue",
            "fact_marketing_spend",
        )
    )
    print(f"wrote {DB}\n  {rows}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
