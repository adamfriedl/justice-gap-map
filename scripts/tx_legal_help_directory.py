"""Texas: how many legal help organizations list each county as one they serve?

Source: the Texas Access to Justice Commission's county resource directory
(texasatj.org, "Get Help"), read through the site's public WordPress API on
2026-11-09 and saved under data/txlegalaid/2026-11-09/:

    for pg in $(seq 1 19); do curl -sS -o tajc_res_$pg.json \
      "https://texasatj.org/wp-json/wp/v2/county-resource?per_page=100&page=$pg&_fields=id,title,county,resource-category,meta,link,modified"; done
    # plus /wp-json/wp/v2/county and /wp-json/wp/v2/resource-category (term names)

Each entry is one organization listed under one county (or "Statewide"), with
practice-area tags. The directory gives coverage, not office locations. It
includes legal aid nonprofits, clinics, immigration services, family violence
programs, public defenders and dispute resolution centers, LSC-funded or not.

    uv run python scripts/tx_legal_help_directory.py --out docs/legal-aid/texas
"""

import argparse
import csv
import glob
import html
import json
from collections import defaultdict
from pathlib import Path

import duckdb

RAW = Path("data/txlegalaid/2026-11-09")
FILINGS = Path("docs/lawsuits/county_filings_tx_in.csv")
CIVIL = {"General Civil Justice", "Consumer/Transactional", "Housing and Utilities"}
LSC = {"Legal Aid Of NorthWest Texas", "Lone Star Legal Aid", "Texas RioGrande Legal Aid (TRLA)"}


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="docs/legal-aid/texas")
    a = p.parse_args()
    out = Path(a.out)

    cats = {c["id"]: c["name"] for f in glob.glob(str(RAW / "tajc_tax_resource-category_*.json")) for c in json.load(open(f))}
    counties = {c["id"]: c["name"] for f in glob.glob(str(RAW / "tajc_tax_county_*.json")) for c in json.load(open(f))}
    fips = {}
    with open("data/census/gazetteer/2024/2024_Gaz_counties_national.txt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            r = {k.strip(): v.strip() for k, v in r.items()}
            if r["USPS"] == "TX":
                fips[r["NAME"].removesuffix(" County").lower()] = (r["GEOID"], r["NAME"].removesuffix(" County"))

    entries = [e for f in sorted(glob.glob(str(RAW / "tajc_res_*.json"))) for e in json.load(open(f))]
    by_county = defaultdict(lambda: {"all": set(), "civil": set(), "consumer": set(), "consumer_non_lsc": set(), "consumer_non_lsc_non_tax": set()})
    orgs = defaultdict(lambda: {"counties": set(), "categories": set(), "statewide": False})
    unmatched = set()
    for e in entries:
        name = html.unescape(e["title"]["rendered"]).strip()
        tags = {cats.get(c, str(c)) for c in e["resource-category"]}
        for cid in e["county"]:
            cname = counties.get(cid, str(cid))
            o = orgs[name]
            o["categories"] |= tags
            if cname == "Statewide":
                o["statewide"] = True
                continue
            if cname.lower() not in fips:
                unmatched.add(cname)
                continue
            o["counties"].add(cname)
            b = by_county[fips[cname.lower()][0]]
            b["all"].add(name)
            if tags & CIVIL:
                b["civil"].add(name)
            if "Consumer/Transactional" in tags:
                b["consumer"].add(name)
                if name not in LSC:
                    b["consumer_non_lsc"].add(name)
                    if "tax" not in name.lower():  # low-income taxpayer clinics: tax disputes, not debt suits
                        b["consumer_non_lsc_non_tax"].add(name)
    if unmatched:
        print("county names not matched:", sorted(unmatched))

    with open(out / "directory_orgs.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["organization", "lsc_funded", "statewide", "counties_listed", "practice_areas", "source", "fetched"])
        for name, o in sorted(orgs.items()):
            w.writerow([name, name in LSC, o["statewide"], len(o["counties"]), "; ".join(sorted(o["categories"])),
                        "https://texasatj.org/legal-help/", "2026-11-09"])
    with open(out / "directory_county.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fips", "county", "orgs_listed", "civil_orgs", "consumer_orgs", "consumer_orgs_non_lsc", "consumer_orgs_non_lsc_non_tax"])
        for fp, cname in sorted(fips.values()):
            b = by_county[fp]
            w.writerow([fp, cname, len(b["all"]), len(b["civil"]), len(b["consumer"]), len(b["consumer_non_lsc"]), len(b["consumer_non_lsc_non_tax"])])

    c = duckdb.connect()
    c.sql(f"""create view j as select d.*, f.filed, f.filed_per_1k, f.reporting_pct, f.pop, f.pct_lt125
      from read_csv_auto('{out / "directory_county.csv"}', types={{'fips': 'VARCHAR'}}) d
      join read_csv_auto('{FILINGS}', types={{'fips': 'VARCHAR'}}) f on f.fips = d.fips and f.state = 'TX' and f.year = 2025""")
    c.sql(f"""copy (
      select case when consumer_orgs_non_lsc_non_tax = 0 then '0' when consumer_orgs_non_lsc_non_tax = 1 then '1'
                  when consumer_orgs_non_lsc_non_tax = 2 then '2' else '3+' end as consumer_orgs_beyond_lsc_and_tax_clinics,
             count(*) as counties, sum(pop) as population,
             sum(filed) filter (where reporting_pct >= 90) as debt_suits_2025_full_reporting,
             round(median(filed_per_1k) filter (where reporting_pct >= 90), 1) as median_suits_per_1k
      from j group by 1 order by 1) to '{out / "directory_bands.csv"}' (header)""")

    def rho(x, y, where="true"):
        return c.sql(f"""select count(*), round(corr(r1, r2), 3) from (
            select rank() over (order by {x}) r1, rank() over (order by {y}) r2 from j where {where})""").fetchall()[0]
    rows = [
        ("TX 2025 debt suits per 1K vs civil legal help orgs listed for the county", *rho("filed_per_1k", "civil_orgs", "reporting_pct >= 90")),
        ("TX 2025 debt suits per 1K vs consumer orgs listed beyond the LSC program and tax clinics", *rho("filed_per_1k", "consumer_orgs_non_lsc_non_tax", "reporting_pct >= 90")),
        ("TX share under 125% poverty vs civil legal help orgs listed", *rho("pct_lt125", "civil_orgs")),
    ]
    with open(out / "directory_checks.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["check", "n", "spearman"])
        w.writerows(rows)
    print(f"{len(entries)} entries, {len(orgs)} organizations; wrote {out}")


if __name__ == "__main__":
    main()
