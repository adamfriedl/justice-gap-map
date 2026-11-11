"""Scheduled ingest job (AWS Lambda): Harris County debt-claim cases, once a day,
into the raw bucket as a dated snapshot.

The download and the privacy filter are scripts/lawsuits_fetch_harris.py, the
same code the local script runs: defendants' names and street addresses are
dropped in memory, so they never reach S3 (PRD R15). This file only picks the
date window and writes the result.

Each run asks for cases filed in the last WINDOW_DAYS days, in one request. The
windows overlap on purpose: a case's status and hearing date change after
filing, and each snapshot records them as of its download date.

A backfill passes its own window, a month at a time:

    {"from": "2026-01-01", "to": "2026-01-31"}

Why the windows are short: the county's server takes about 55 seconds to build
a 31-day extract (9,854 rows, measured 2026-11-11), and a 179-day request timed
out at the site's proxy (HTTP 524). The service's own limit is 180 days.

The extract has one row per case and party, so a case with two defendants
appears twice (about 5% more rows than cases). Rows are stored as received;
count distinct case numbers downstream.
"""

import csv
import datetime as dt
import io
import os

from lawsuits_fetch_harris import KEEP, fetch

WINDOW_DAYS = 14
MAX_DAYS = 31  # longer requests risk the timeout described above
FIELDS = KEEP + ["Defendant Has Attorney"]


def window(today: dt.date, event: dict) -> tuple[dt.date, dt.date]:
    """Filing dates to ask for: yesterday and the days before it, unless the event says otherwise."""
    if "from" in event or "to" in event:
        start, end = dt.date.fromisoformat(event["from"]), dt.date.fromisoformat(event["to"])
    else:
        end = today - dt.timedelta(days=1)
        start = end - dt.timedelta(days=WINDOW_DAYS - 1)
    days = (end - start).days + 1
    if not 1 <= days <= MAX_DAYS:
        raise ValueError(f"window {start} to {end} is {days} days; must be 1 to {MAX_DAYS}")
    return start, end


def to_csv(rows: list[dict]) -> bytes:
    """Only FIELDS can be written: DictWriter raises on any other column."""
    buf = io.StringIO(newline="")
    w = csv.DictWriter(buf, fieldnames=FIELDS, extrasaction="raise")
    w.writeheader()
    w.writerows(rows)
    return buf.getvalue().encode("utf-8")


def key_for(today: dt.date, start: dt.date, end: dt.date) -> str:
    return f"harris/debt_claims_filed/downloaded={today}/filed_{start}_{end}.csv"


def handler(event, context, s3=None, today=None):
    today = today or dt.datetime.now(dt.timezone.utc).date()
    start, end = window(today, event or {})
    rows = fetch(start, end)
    if not rows:
        # Harris County files hundreds of debt claims a day. An empty answer
        # means the source changed or failed, so fail the run instead of
        # archiving an empty snapshot.
        raise RuntimeError(f"no cases returned for {start} to {end}")
    if s3 is None:
        import boto3  # in the Lambda runtime; not a project dependency

        s3 = boto3.client("s3")
    key = key_for(today, start, end)
    # The raw bucket's Object Lock requires a checksum on every upload.
    s3.put_object(
        Bucket=os.environ["RAW_BUCKET"], Key=key, Body=to_csv(rows),
        ContentType="text/csv", ChecksumAlgorithm="SHA256",
    )
    cases = len({r["Case Number"] for r in rows})
    # Counts only. Rows never go to the logs.
    print(f"wrote s3://{os.environ['RAW_BUCKET']}/{key} ({len(rows)} rows, {cases} cases filed {start} to {end})")
    return {"key": key, "rows": len(rows), "cases": cases, "from": str(start), "to": str(end)}
