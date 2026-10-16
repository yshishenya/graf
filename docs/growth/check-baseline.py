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
    ("included", "external", "direct", 3, "2026-10-01"),
    ("included", "external", "direct", 4, "2026-10-02"),
    *[("small", "external", "direct", 1, "2026-10-01")] * 5,
    ("robot", "automated", "direct", 30, "2026-10-01"),
    ("late", "external", "direct", 20, "2026-10-15"),
])
# SQLite supports the aggregate syntax; DATE literals become ISO strings.
queries = [query.replace("DATE '", "'") for query in queries[:2]]
assert db.execute(queries[0]).fetchall() == [(2, 7, "2026-10-01", "2026-10-02")]
assert db.execute(queries[1]).fetchall() == [("included", "external", "direct", 7)]
print("PASS: source buckets, external traffic, window and grouped totals")
