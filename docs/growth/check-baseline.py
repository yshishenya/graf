"""Run with python3 docs/growth/check-baseline.py; no production connection."""

import sqlite3
from pathlib import Path

sql = Path(__file__).with_name("baseline-2026-10-16.sql").read_text()
queries = [part.strip() for part in sql.split(";") if part.strip().startswith("SELECT")]
db = sqlite3.connect(":memory:")
db.execute("CREATE TABLE anonymous_page_aggregate_buckets "
           "(surface TEXT, traffic_class TEXT, referrer_category TEXT, "
           "visits INTEGER, bucket_date TEXT)")
db.executemany("INSERT INTO anonymous_page_aggregate_buckets VALUES (?,?,?,?,?)", [
    ("public_landing", "external", "direct", 3, "2026-10-01"),
    ("public_landing", "external", "direct", 4, "2026-10-02"),
    *[("public_download", "external", "direct", 1, "2026-10-01")] * 5,
    ("public_login", "automated", "direct", 30, "2026-10-01"),
    ("public_privacy", "external", "direct", 20, "2026-10-15"),
    ("public_signup_step_viewed", "external", "unknown", 9, "2026-10-01"),
    ("unknown_future", "external", "direct", 5, "2026-10-01"),
])
# SQLite supports the aggregate syntax; DATE literals become ISO strings.
queries = [query.replace("DATE '", "'") for query in queries[:2]]
assert db.execute(queries[0]).fetchall() == [
    ("actions", 1, 9, "2026-10-01", "2026-10-01"),
    ("other_signals", 1, 5, "2026-10-01", "2026-10-01"),
    ("page_requests", 2, 7, "2026-10-01", "2026-10-02"),
]
assert db.execute(queries[1]).fetchall() == [
    ("public_landing", "external", "direct", 7),
    ("public_signup_step_viewed", "external", "unknown", 9),
    ("unknown_future", "external", "direct", 5),
]
print("PASS: source buckets, external traffic, window, separate pages/actions/unknown and grouped totals")
