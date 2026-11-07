"""Where debt lawsuits are filed: county debt-case filings for the states with
open court data, per 1,000 residents, with default rates where courts report them.

States and sources (raw files from the fetch scripts, under data/):
- Texas: OCA justice-court "Debt Claim" cases (scripts/phase0_tx_courts_fetch.py).
- Indiana: ICOR "Collection" (CC) cases, all courts in the county (scripts/lawsuits_fetch_indiana.py).
- Virginia: General District Court "General Civil & Civil Commitments" filings,
  2025 (mostly warrants in debt; see the write-up), plus garnishments.
  Calibrated against LSC's Baseline Court Statistics warrant-in-debt counts, 2016-2019.

    uv run python scripts/lawsuits.py --out docs/lawsuits
"""

import argparse
import glob
import json
import re
from pathlib import Path

import duckdb
import pypdf
import xlrd

from phase0_need import NORM_COUNTY, parse_tx_rows

TX_DIRS = ["data/txcourts/2026-11-06", "data/txcourts/2026-11-07"]
IN_DIR = "data/incourts/2026-11-07"
VA_PDF = "data/vacourts/2026-11-07/gdc_filings.pdf"
BCS = "data/lsc/bcs/bcs_dataset_2023-05-01.csv"
ACS = "data/acs/county_acs5_2024.json"
URBAN = "data/urban/2025-11-20/county_overall.csv"

VA_CATS = ["Felony", "Garnishment", "General Civil & Civil Commitments", "Infraction/Civil Violation",
           "Landlord/Tenant", "Misdemeanor", "Not Tracked For Judicial Workload", "Other", "Protective Orders",
           "Locale Total"]
# Independent cities with no General District Court of their own, and combined
# courts: the county-equivalents each court serves (FIPS). Courts not listed
# serve the one locality whose name they carry.
VA_COURT_EXTRA = {
    "Alleghany": ["51005", "51580"],          # + Covington city
    "Prince William": ["51153", "51683", "51685"],  # + Manassas, Manassas Park
    "Wise": ["51195", "51720"],               # + Norton city
    "York": ["51199", "51735"],               # + Poquoson city
    "Lexington/Rockb": ["51163", "51678"],    # Rockbridge County + Lexington city
    "Rockingham/Har": ["51165", "51660"],     # Rockingham County + Harrisonburg city
    "Williamsburg/Ja": ["51095", "51830"],    # James City County + Williamsburg city
    "Richmond": ["51159"],                    # Richmond County (Richmond City is separate)
    "Bedford": ["51019"],
    "Charles City": ["51036"],                # Charles City County
}


def read_tx(con) -> None:
    rows = []
    for d in TX_DIRS:
        for path in sorted(glob.glob(f"{d}/*/*.xls")):
            year = int(Path(path).parent.name)
            sheet = xlrd.open_workbook(path).sheet_by_index(0)
            r = parse_tx_rows([[str(c) for c in sheet.row_values(i)] for i in range(sheet.nrows)])
            rows.append(("TX", r.get("county_name"), year, r.get("debt_filed"), r.get("debt_default"),
                         r.get("debt_disposed"), r.get("reporting_pct"), None))
        for path in sorted(glob.glob(f"{d}/*/statewide/*.xls")):
            year = int(Path(path).parent.parent.name)
            sheet = xlrd.open_workbook(path).sheet_by_index(0)
            r = parse_tx_rows([[str(c) for c in sheet.row_values(i)] for i in range(sheet.nrows)])
            rows.append(("TX", "(statewide)", year, r.get("debt_filed"), r.get("debt_default"),
                         r.get("debt_disposed"), r.get("reporting_pct"), None))
    con.executemany("INSERT INTO raw VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)


def in_cells(grid: dict, row_title: str, code: str):
    """Value of one row (e.g. 'New Filings') for one case-type code (e.g. 'CC')."""
    for t in grid["Tables"]:
        cols = [c["Title3"] for s in t["ColumnSections"] for c in s["Columns"]]
        if code not in cols:
            continue
        i = cols.index(code)
        for rs in t["RowSections"]:
            for r in rs["Rows"]:
                if not r.get("isTitle") and r["Title"] == row_title:
                    v = (r["Cells"][i].get("TxtVal") or "").replace(",", "")
                    return float(v) if re.fullmatch(r"-?\d+(\.\d+)?", v) else None
    return None


def read_in(con) -> None:
    rows = []
    for path in sorted(glob.glob(f"{IN_DIR}/*/*.json")):
        d = json.loads(Path(path).read_text())
        g, year = d["grid"], int(Path(path).parent.name)
        name = d["county"].replace(" County", "")
        rows.append(("IN", name, year, in_cells(g, "New Filings", "CC"), in_cells(g, "Default", "CC"),
                     in_cells(g, "TOTAL DISPOSED CASES", "CC"), None, in_cells(g, "New Filings", "SC")))
    con.executemany("INSERT INTO raw VALUES (?, ?, ?, ?, ?, ?, ?, ?)", rows)


def parse_va(path: str, year: str = "2025") -> dict:
    out, locale, cat = {}, None, None
    for page in pypdf.PdfReader(path).pages[1:]:
        lines = [x.strip() for x in (page.extract_text() or "").split("\n")]
        i = 0
        while i < len(lines):
            line = lines[i]
            if line.endswith(("Civil", "Judicial")) and i + 1 < len(lines) and lines[i + 1] in ("Commitments", "Workload"):
                line, i = line + " " + lines[i + 1], i + 1
            m = re.match(r"^(\d{1,2}[A-Z]?)\s+([A-Za-z].*)$", line)
            if m and not line.startswith("District Total"):
                locale, cat = m.group(2).strip(), None
            elif line.startswith("(") and ")" in line and locale:
                rest = line[line.index(")") + 1:].strip()
                cat = rest if rest in VA_CATS else cat
            elif line in VA_CATS:
                cat = line
            elif line.startswith(year + " ") and locale and cat:
                out.setdefault(locale, {})[cat] = int(line.split()[-1].replace(",", ""))
            i += 1
    return out


def va_units(con, va: dict) -> None:
    """Map each Virginia court to the county-equivalents it serves."""
    acs = con.sql("SELECT fips, name FROM acs WHERE state_fips = '51'").fetchall()
    by_name = {}
    for fips, name in acs:
        place = name.split(",")[0]
        by_name[place.lower()] = fips
    rows, unmatched = [], []
    for court, cats in va.items():
        if court in VA_COURT_EXTRA:
            fipses = VA_COURT_EXTRA[court]
        else:
            base = court.replace(" City", "").replace(" County", "").replace("Isle Of Wight", "Isle of Wight") \
                        .replace("King & Queen", "King and Queen")
            base = re.sub(r"\s*\(District \w+\)", "", base)
            if court.endswith(" City"):
                keys = [f"{base} city"]
            elif court.endswith(" County"):
                keys = [f"{base} county"]
            else:
                keys = [f"{base} city", f"{base} county"]
            fipses = [by_name[k.lower()] for k in keys if k.lower() in by_name][:1]
        if not fipses:
            unmatched.append(court)
        for f in fipses:
            rows.append((court, f, cats.get("General Civil & Civil Commitments"), cats.get("Garnishment"),
                         cats.get("Landlord/Tenant")))
    if unmatched:
        print("Virginia courts not matched to a locality:", unmatched)
    con.sql("CREATE TABLE va_court (court VARCHAR, fips VARCHAR, general_civil INT, garnishment INT, landlord_tenant INT)")
    con.executemany("INSERT INTO va_court VALUES (?, ?, ?, ?, ?)", rows)


def write(con, sql: str, path: Path) -> None:
    con.sql(f"COPY ({sql}) TO '{path}' (HEADER, DELIMITER ',')")
    print(f"wrote {path}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="docs/lawsuits")
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    con.sql(NORM_COUNTY)
    con.sql(f"""
        CREATE TABLE acs AS
        WITH raw AS (SELECT unnest(j) AS r FROM (SELECT json(content)::VARCHAR[][] AS j FROM read_text('{ACS}')))
        SELECT r[7] || r[8] AS fips, r[1] AS name, r[7] AS state_fips, r[2]::INT AS pop,
               (r[4]::INT + r[5]::INT + r[6]::INT) AS pop_lt125
        FROM raw WHERE r[1] <> 'NAME'
    """)
    con.sql(f"""CREATE TABLE urban AS SELECT id AS fips, totcoll FROM read_csv('{URBAN}', nullstr='NA',
                types={{'id': 'VARCHAR', 'state_id': 'VARCHAR'}})""")
    con.sql("""CREATE TABLE raw (state VARCHAR, county VARCHAR, year INT, filed DOUBLE, defaults DOUBLE,
               disposed DOUBLE, reporting_pct DOUBLE, small_claims_filed DOUBLE)""")
    read_tx(con)
    read_in(con)

    # County table for TX and IN: join names to ACS FIPS within the state.
    con.sql("""
        CREATE TABLE county AS
        SELECT r.state, a.fips, r.county, r.year, r.filed, r.defaults, r.disposed, r.reporting_pct,
               r.small_claims_filed, a.pop, round(100.0 * a.pop_lt125 / a.pop, 1) AS pct_lt125,
               round(100 * u.totcoll, 1) AS pct_in_collections,
               round(1000 * r.filed / a.pop, 2) AS filed_per_1k,
               round(100 * r.defaults / nullif(r.disposed, 0), 1) AS pct_default
        FROM raw r
        JOIN acs a ON a.state_fips = CASE r.state WHEN 'TX' THEN '48' WHEN 'IN' THEN '18' END
             AND norm_county(r.county) = norm_county(replace(split_part(a.name, ',', 1), ' County', ''))
        LEFT JOIN urban u ON u.fips = a.fips
    """)
    missing = con.sql("""SELECT DISTINCT state, county FROM raw WHERE county <> '(statewide)'
                         AND (state, county) NOT IN (SELECT state, county FROM county)""").fetchall()
    if missing:
        print("Counties not matched to ACS:", missing)

    # Virginia: 2025 court-level counts, spread to the localities each court serves.
    va_units(con, parse_va(VA_PDF))
    con.sql(f"""
        CREATE TABLE va AS
        WITH u AS (SELECT court, any_value(general_civil) AS general_civil, any_value(garnishment) AS garnishment,
                          any_value(landlord_tenant) AS landlord_tenant, sum(pop) AS pop,
                          sum(pop_lt125) AS pop_lt125, list(fips) AS fipses
                   FROM va_court JOIN acs USING (fips) GROUP BY court),
             wid AS (SELECT fips, avg(try_cast(count_filings AS INT)) AS wid_per_year
                     FROM read_csv('{BCS}', all_varchar=true)
                     WHERE state = 'virginia' AND case_type = 'warrant in debt' AND year_filed BETWEEN '2016' AND '2019'
                     GROUP BY fips)
        SELECT u.court, u.fipses, u.pop, round(100.0 * u.pop_lt125 / u.pop, 1) AS pct_lt125,
               u.general_civil, round(1000.0 * u.general_civil / u.pop, 2) AS general_civil_per_1k,
               u.garnishment, round(1000.0 * u.garnishment / u.pop, 2) AS garnishment_per_1k,
               u.landlord_tenant,
               round(w.wid, 0) AS warrants_in_debt_2016_19_avg,
               round(1000.0 * w.wid / u.pop, 2) AS wid_2016_19_per_1k
        FROM u LEFT JOIN (
            SELECT court, sum(wid_per_year) AS wid FROM va_court JOIN wid USING (fips) GROUP BY court
        ) w USING (court)
    """)

    write(con, "SELECT * FROM county WHERE county <> '(statewide)' ORDER BY state, county, year",
          out / "county_filings_tx_in.csv")
    write(con, "SELECT court, array_to_string(fipses, ' ') AS fips, * EXCLUDE (court, fipses) FROM va ORDER BY court",
          out / "virginia_courts_2025.csv")
    write(con, """
        SELECT state, year, sum(filed) AS filed, sum(defaults) AS defaults, sum(disposed) AS disposed,
               round(100 * sum(defaults) / sum(disposed), 1) AS pct_default, count(*) AS rows
        FROM (SELECT * FROM raw WHERE state = 'TX' AND county = '(statewide)'
              UNION ALL SELECT * FROM raw WHERE state = 'IN')
        GROUP BY ALL ORDER BY state, year
    """, out / "state_trend.csv")

    # Rank checks: does geography hold over time, and does Virginia's 2025
    # General Civil line track true warrants in debt (2016-2019)?
    def rho(table, x, y, where="true"):
        return con.sql(f"""SELECT count(*), round(corr(rx, ry), 3) FROM (
            SELECT rank() OVER (ORDER BY {x}) rx, rank() OVER (ORDER BY {y}) ry FROM {table}
            WHERE {where} AND {x} IS NOT NULL AND {y} IS NOT NULL)""").fetchall()[0]
    checks = []
    for st, y0, y1 in [("TX", 2019, 2025), ("TX", 2023, 2025), ("IN", 2014, 2024)]:
        con.sql(f"""CREATE OR REPLACE TEMP TABLE pair AS
            SELECT a.filed_per_1k AS a, b.filed_per_1k AS b, a.pop FROM county a JOIN county b USING (state, fips)
            WHERE a.state = '{st}' AND a.year = {y0} AND b.year = {y1}
              AND coalesce(a.reporting_pct, 100) >= 90 AND coalesce(b.reporting_pct, 100) >= 90""")
        checks.append((f"{st} filings per 1K, {y0} vs {y1} (Spearman)", *rho("pair", "a", "b")))
    checks.append(("VA 2025 general civil per 1K vs 2016-19 warrants in debt per 1K",
                   *rho("va", "general_civil_per_1k", "wid_2016_19_per_1k")))
    checks.append(("VA 2025 garnishments per 1K vs 2016-19 warrants in debt per 1K",
                   *rho("va", "garnishment_per_1k", "wid_2016_19_per_1k")))
    for st, yr in [("TX", 2025), ("IN", 2024)]:
        checks.append((f"{st} {yr} filings per 1K vs share under 125% poverty",
                       *rho("county", "filed_per_1k", "pct_lt125",
                            f"state = '{st}' AND year = {yr} AND coalesce(reporting_pct, 100) >= 90")))
        checks.append((f"{st} {yr} filings per 1K vs debt in collections",
                       *rho("county", "filed_per_1k", "pct_in_collections",
                            f"state = '{st}' AND year = {yr} AND coalesce(reporting_pct, 100) >= 90")))
    checks.append(("VA 2025 general civil per 1K vs share under 125% poverty", *rho("va", "general_civil_per_1k", "pct_lt125")))
    con.sql("CREATE TABLE checks (check_name VARCHAR, n INT, spearman DOUBLE)")
    con.executemany("INSERT INTO checks VALUES (?, ?, ?)", checks)
    write(con, "SELECT * FROM checks", out / "checks.csv")


if __name__ == "__main__":
    main()
