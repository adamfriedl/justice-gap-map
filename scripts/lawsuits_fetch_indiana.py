"""Download Indiana trial-court caseload statistics by county (Indiana Court
Online Reports, https://publicaccess.courts.in.gov/ICOR/).

Uses the JSON API behind the ICOR dashboard: for each county and year, the
"All <County> Courts" data grid (the Quarterly Case Status Report). Raw JSON
lands under data/incourts/<download date>/<year>/<county code>.json. Stdlib only.

    uv run python scripts/lawsuits_fetch_indiana.py --years 2014 2024
"""

import argparse
import datetime as dt
import json
import time
import urllib.request
from pathlib import Path

BASE = "https://publicaccess.courts.in.gov/icor/api/"
UA = {"User-Agent": "justice-gap-map research (Python urllib)"}


def get(path: str, tries: int = 5):
    for attempt in range(tries):
        try:
            with urllib.request.urlopen(urllib.request.Request(BASE + path, headers=UA), timeout=120) as r:
                return json.loads(r.read())
        except Exception as e:  # cut-off transfers happen on long runs
            if attempt == tries - 1:
                raise
            print(f"retry {path}: {e}")
            time.sleep(2 ** (attempt + 1))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--years", type=int, nargs=2, default=[2014, 2024], metavar=("FROM", "TO"))
    p.add_argument("--out", default=f"data/incourts/{dt.date.today():%Y-%m-%d}")
    p.add_argument("--pause", type=float, default=0.3)
    a = p.parse_args()
    counties = [c for c in get("DropDown/GetDropDown?DropDown=County&Mode=Certified") if c["Value"] != "00"]
    print(f"{len(counties)} counties")
    for year in range(a.years[0], a.years[1] + 1):
        out = Path(a.out) / str(year)
        out.mkdir(parents=True, exist_ok=True)
        for c in counties:
            path = out / f"{c['Value']}.json"
            if path.exists():
                continue
            courts = get(f"DropDown/GetCourtDropDown?CountyCode={c['Value']}&Year={year}")
            # "All <County> Courts" includes city and town courts; "All ... Trial Courts" doesn't.
            # Collection cases are filed in trial courts, but take the broader total to be safe.
            allc = [x for x in courts if x["Name"].startswith("All ") and "Trial" not in x["Name"]] or courts[:1]
            if not allc:
                print(f"{year} {c['Name']}: no courts")
                continue
            grid = get(f"Report/GetDataGrid?CourtID={allc[0]['Value']}&Year={year}")
            path.write_text(json.dumps({"county_code": c["Value"], "county": c["Name"], "court": allc[0], "grid": grid}))
            time.sleep(a.pause)
        print(f"{year}: done")


if __name__ == "__main__":
    main()
