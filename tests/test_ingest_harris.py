import csv
import datetime as dt
import io
import sys
from pathlib import Path

import pytest

root = Path(__file__).parent.parent
sys.path.insert(0, str(root / "scripts"))
sys.path.insert(0, str(root / "src"))
import ingest_harris  # noqa: E402
from lawsuits_fetch_harris import safe_row  # noqa: E402

TODAY = dt.date(2026, 11, 11)
RAW_ROW = {
    "Case Number": "123", "Style Of Case": "LVNV FUNDING LLC VS JANE DOE", "Plaintiff Name": "Lvnv Funding Llc",
    "Defendant Name": "JANE DOE", "Defendant Addr Line 1": "1 MAIN ST", "Defendant Addr Zip": "77002-1234",
    "Defendant Atty Name": "", "Judgment Against": "JANE DOE",
}


class FakeS3:
    def __init__(self):
        self.puts = []

    def put_object(self, **kw):
        self.puts.append(kw)


def test_default_window_is_the_14_days_ending_yesterday():
    assert ingest_harris.window(TODAY, {}) == (dt.date(2026, 10, 28), dt.date(2026, 11, 10))


def test_backfill_window_comes_from_the_event_and_is_capped():
    assert ingest_harris.window(TODAY, {"from": "2026-01-01", "to": "2026-01-31"}) == (
        dt.date(2026, 1, 1), dt.date(2026, 1, 31))
    with pytest.raises(ValueError):
        ingest_harris.window(TODAY, {"from": "2026-01-01", "to": "2026-02-01"})  # 32 days
    with pytest.raises(ValueError):
        ingest_harris.window(TODAY, {"from": "2026-03-02", "to": "2026-03-01"})  # backwards
    with pytest.raises(KeyError):
        ingest_harris.window(TODAY, {"from": "2026-01-01"})


def test_handler_writes_one_dated_object_without_defendant_identifiers(monkeypatch):
    monkeypatch.setenv("RAW_BUCKET", "raw-bucket")
    # Two rows for one case: the extract repeats a case for each party.
    monkeypatch.setattr(ingest_harris, "fetch", lambda start, end: [safe_row(RAW_ROW), safe_row(RAW_ROW)])
    s3 = FakeS3()
    out = ingest_harris.handler({}, None, s3=s3, today=TODAY)

    assert len(s3.puts) == 1
    put = s3.puts[0]
    assert put["Bucket"] == "raw-bucket"
    assert put["Key"] == "harris/debt_claims_filed/downloaded=2026-11-11/filed_2026-10-28_2026-11-10.csv"
    assert put["ChecksumAlgorithm"] == "SHA256"  # Object Lock refuses uploads without a checksum
    assert out == {"key": put["Key"], "rows": 2, "cases": 1, "from": "2026-10-28", "to": "2026-11-10"}

    body = put["Body"].decode()
    for secret in ["JANE", "MAIN ST", "DOE"]:
        assert secret not in body
    rows = list(csv.DictReader(io.StringIO(body)))
    assert list(rows[0]) == ingest_harris.FIELDS
    assert rows[0]["Defendant Addr Zip"] == "77002" and rows[0]["Plaintiff Name"] == "Lvnv Funding Llc"


def test_a_column_outside_the_allowed_list_cannot_be_written():
    with pytest.raises(ValueError):
        ingest_harris.to_csv([{**safe_row(RAW_ROW), "Defendant Name": "JANE DOE"}])


def test_an_empty_download_fails_the_run_and_writes_nothing(monkeypatch):
    monkeypatch.setenv("RAW_BUCKET", "raw-bucket")
    monkeypatch.setattr(ingest_harris, "fetch", lambda start, end: [])
    s3 = FakeS3()
    with pytest.raises(RuntimeError):
        ingest_harris.handler({}, None, s3=s3, today=TODAY)
    assert s3.puts == []


def test_athena_table_columns_match_the_csv_the_job_writes():
    """infra/main/harris_table.tf lists the table's columns by position; they must follow FIELDS."""
    import re
    tf = (root / "infra" / "main" / "harris_table.tf").read_text()
    block = tf[tf.index("harris_columns = ["):]
    cols = re.findall(r'"([a-z_]+)"', block[:block.index("]")])
    assert cols == [f.lower().replace(" ", "_") for f in ingest_harris.FIELDS]
