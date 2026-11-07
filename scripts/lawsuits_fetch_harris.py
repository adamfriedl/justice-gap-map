"""Download debt-claim cases filed in Harris County (Texas) justice courts, from
the county's official JP Public Data Extract Service
(https://jpwebsite.harriscountytx.gov/PublicExtracts/search.jsp).

Privacy rule: people sued are private individuals, so their names and street
addresses never reach disk. Each row is reduced in memory to the fields below.
For defendants that means only ZIP code and whether they had an attorney.
"Style of Case" and "Judgment Against" are dropped because they contain names.
Plaintiffs (debt buyers, collectors, lenders) and their attorneys are kept.

    uv run python scripts/lawsuits_fetch_harris.py --from 2026-10-01 --to 2026-10-07

Output: data/harris/<download date>/debt_claims_filed_<from>_<to>.csv
"""

import argparse
import csv
import datetime as dt
import io
import urllib.parse
import urllib.request
from pathlib import Path

URL = "https://jpwebsite.harriscountytx.gov/PublicExtracts/GetExtractData"
UA = {"User-Agent": "justice-gap-map research (Python urllib)"}
DEBT_CLAIM = "8463"
CASES_FILED = "7"
ALL_COURTS = "300"

KEEP = [
    "Case Number", "JP Court ID", "Case Type", "Case File Date", "Cause of Action", "Claim Amount",
    "Case Status", "Plaintiff Name", "Plaintiff Addr City", "Plaintiff Addr State", "Plaintiff Addr Zip",
    "Plaintiff Atty Name", "Defendant Addr Zip", "Next Hearing Desc", "Next Hearing Date",
    "Disposition Desc", "Disposition Date", "Judgment Text", "Judgment Date", "Judgment Amount",
    "Attorney Fees", "Court Costs",
]


def safe_row(row: dict) -> dict:
    row = {(k or "").strip(): v for k, v in row.items()}  # the extract pads some headers with spaces
    out = {k: (row.get(k) or "").strip() for k in KEEP}
    out["Defendant Addr Zip"] = out["Defendant Addr Zip"][:5]
    out["Defendant Has Attorney"] = "Y" if (row.get("Defendant Atty Name") or "").strip() else "N"
    return out


def fetch(start: dt.date, end: dt.date) -> list[dict]:
    q = urllib.parse.urlencode({
        "extractCaseType": "CV", "extract": CASES_FILED, "court": ALL_COURTS, "casetype": DEBT_CLAIM,
        "format": "csv", "fdate": f"{start:%m/%d/%Y}", "tdate": f"{end:%m/%d/%Y}",
    })
    with urllib.request.urlopen(urllib.request.Request(f"{URL}?{q}", headers=UA), timeout=600) as r:
        text = r.read().decode("latin-1")
    reader = csv.DictReader(io.StringIO(text))
    names = [(h or "").strip() for h in (reader.fieldnames or [])]
    missing = [k for k in KEEP + ["Defendant Atty Name"] if k not in names]
    if missing:
        raise RuntimeError(f"extract layout changed; missing columns: {missing}; got {names[:8]}")
    return [safe_row(r) for r in reader]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--from", dest="start", required=True, type=dt.date.fromisoformat)
    p.add_argument("--to", dest="end", required=True, type=dt.date.fromisoformat)
    p.add_argument("--out", default=f"data/harris/{dt.date.today():%Y-%m-%d}")
    a = p.parse_args()
    rows = fetch(a.start, a.end)
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    path = out / f"debt_claims_filed_{a.start}_{a.end}.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=KEEP + ["Defendant Has Attorney"])
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} cases)")


if __name__ == "__main__":
    main()
