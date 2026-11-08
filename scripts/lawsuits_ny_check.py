"""New York check: what does LSC's Baseline Court Statistics hold for New York?

New York's court sites (nycourts.gov, iapps.courts.state.ny.us) answer scripts
with a Cloudflare challenge page (HTTP 403), so this check uses the copy of
LSC's Baseline Court Statistics already downloaded for the lawsuits track.

    uv run python scripts/lawsuits_ny_check.py --out docs/lawsuits/new-york
"""

import argparse
from pathlib import Path

import duckdb

BCS = "data/lsc/bcs/bcs_dataset_2023-05-01.csv"


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bcs", default=BCS)
    p.add_argument("--out", default="docs/lawsuits/new-york")
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    c = duckdb.connect()
    c.sql(f"create view bcs as select * from read_csv_auto('{a.bcs}') where state = 'new york'")
    c.sql("""
        copy (
          select coalesce(court_type, 'outside NYC (court type not given)') as court,
                 case_type, min(year_filed) as first_year, max(year_filed) as last_year,
                 count(distinct county) as counties, sum(count_filings) as filings_all_years
          from bcs group by all order by court, filings_all_years desc
        ) to '""" + str(out / "bcs_case_types.csv") + "' (header)")
    c.sql("""
        copy (
          select year_filed as year,
                 sum(count_filings) filter (where court_type = 'new york city civil court' and case_type = 'civil filings') as nyc_civil,
                 sum(count_filings) filter (where court_type is null and case_type = 'civil') as outside_nyc_civil,
                 sum(count_filings) filter (where court_type = 'new york city civil court' and case_type = 'small claims filings') as nyc_small_claims,
                 sum(count_filings) filter (where court_type is null and case_type = 'small claims') as outside_nyc_small_claims
          from bcs group by year order by year
        ) to '""" + str(out / "bcs_civil_by_year.csv") + "' (header)")
    print(f"wrote {out}/bcs_case_types.csv and bcs_civil_by_year.csv")


if __name__ == "__main__":
    main()
