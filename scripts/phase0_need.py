"""Phase 0: do CFPB debt-collection complaints measure need?

Three parts, all written as CSVs to --out:

1. The 2024-26 complaint surge: what changed between the pre-surge years and 2025
   (channel, issue and debt-type mix, company concentration, same-day batches).
2. National: county complaint rates vs. the Urban Institute's share of people with
   debt in collections (credit bureau data, August 2025).
3. Texas: county complaint rates vs. justice-court debt-claim filings (OCA) and vs.
   debt in collections.

    uv run python scripts/phase0_need.py \
        --complaints data/cfpb/2026-11-06/complaints.csv \
        --hud data/hud/zip_county_20262.json \
        --urban data/urban/2025-11-20/county_overall.csv \
        --acs data/acs/county_acs5_2024.json \
        --tx data/txcourts/2026-11-06 \
        --out docs/phase0/need

Correlations are Spearman (rank) correlations across counties, computed as the
Pearson correlation of ranks.
"""

import argparse
import re
from pathlib import Path

import duckdb
import xlrd

PRODUCT = "Debt collection"
BUREAUS = ("EQUIFAX, INC.", "TRANSUNION INTERMEDIATE HOLDINGS, INC.", "Experian Information Solutions Inc.")
PRE_SURGE = (2019, 2023)  # pre-surge baseline years, inclusive; 2020-21 had pandemic relief
MIN_POP = 50_000  # main county sample: small counties have masked ZIPs and noisy rates
MIN_REPORTING = 90.0  # Texas: share of a county's expected monthly court reports received


def num(s) -> float:
    s = str(s).replace(",", "").strip()
    return float(s) if s not in ("", "---") else 0.0


def parse_tx_rows(rows: list[list[str]]) -> dict:
    """Pull the civil debt-claim figures out of one OCA 'Activity Detail' sheet.

    `rows` is the sheet as lists of cell strings, empty cells included, so column
    positions hold. The civil table's header row gives the Debt Claim column
    (other columns are offset by merged cells, so only that one is read). Blank
    or "---" cells count as zero.
    """
    out = {}
    debt_col = None
    for row in rows:
        cells = [c.replace("\xa0", " ").strip() for c in row]
        filled = [c for c in cells if c]
        if not filled:
            continue
        head = filled[0]
        if m := re.match(r"([\d.]+) Percent Reporting Rate", head):
            out["reporting_pct"] = float(m.group(1))
        elif m := re.match(r"(\d+) Reports Received Out of a Possible (\d+)", head):
            out["reports_received"], out["reports_possible"] = int(m.group(1)), int(m.group(2))
        elif head.startswith("County:"):
            out["county_name"] = head.split(":", 1)[1].strip()
        elif head == "Debt Claim":
            debt_col = cells.index("Debt Claim")
        elif debt_col is not None and head in ("New Cases Filed", "Default Judgments", "Total Cases Disposed"):
            key = {"New Cases Filed": "debt_filed", "Default Judgments": "debt_default",
                   "Total Cases Disposed": "debt_disposed"}[head]
            out[key] = num(cells[debt_col])
            if head == "Total Cases Disposed":
                debt_col = None  # the civil table ends here
    return out


def read_tx(tx_dir: Path) -> list[dict]:
    recs = []
    for path in sorted(tx_dir.glob("*/*.xls")):
        sheet = xlrd.open_workbook(str(path)).sheet_by_index(0)
        rows = [[str(c) for c in sheet.row_values(r)] for r in range(sheet.nrows)]
        rec = parse_tx_rows(rows)
        rec["year"] = int(path.parent.name)
        recs.append(rec)
    return recs


NORM_COUNTY = "CREATE MACRO norm_county(s) AS lower(regexp_replace(s, '[^A-Za-z]', '', 'g'))"


def spearman(table: str, x: str, y: str, where: str = "true") -> str:
    """SQL for n and Spearman rho between two columns."""
    return f"""
        SELECT count(*) AS n, round(corr(rx, ry), 3) AS spearman
        FROM (SELECT rank() OVER (ORDER BY {x}) AS rx, rank() OVER (ORDER BY {y}) AS ry
              FROM {table} WHERE {where} AND {x} IS NOT NULL AND {y} IS NOT NULL)
    """


def spearman_within_state(table: str, x: str, y: str, where: str = "true") -> str:
    """Spearman rho on ranks taken within each state, so state-level differences
    (regional debt levels, state awareness of the CFPB) drop out."""
    return f"""
        SELECT count(*) AS n, round(corr(rx, ry), 3) AS spearman
        FROM (SELECT percent_rank() OVER (PARTITION BY state_fips ORDER BY {x}) AS rx,
                     percent_rank() OVER (PARTITION BY state_fips ORDER BY {y}) AS ry
              FROM {table} WHERE {where} AND {x} IS NOT NULL AND {y} IS NOT NULL)
    """


def build(con, a) -> None:
    src = (f"read_parquet('{a.complaints}')" if a.complaints.endswith(".parquet")
           else f"read_csv('{a.complaints}', all_varchar=true, header=true)")
    con.sql(f"""
        CREATE TABLE dc AS
        SELECT "Complaint ID" AS id, CAST("Date received" AS DATE) AS dt,
               year(CAST("Date received" AS DATE)) AS year,
               State AS state, "ZIP code" AS zip, Company AS company, Issue AS issue,
               "Sub-product" AS sub_product, "Submitted via" AS via, Tags AS tags,
               Company IN {BUREAUS} AS bureau,
               regexp_full_match(coalesce("ZIP code", ''), '[0-9]{{5}}') AS has_zip5
        FROM {src} WHERE Product = '{PRODUCT}'
    """)
    # Same-day batches: complaints from one ZIP on one day, against 3+ companies.
    # The placebo is the same ZIP one week later, to show what chance alone gives.
    con.sql("""
        CREATE TABLE zipday AS
        SELECT dt, zip, count(*) AS n, count(DISTINCT company) AS companies,
               count(DISTINCT company) FILTER (bureau) AS bureaus
        FROM dc WHERE has_zip5 GROUP BY ALL
    """)
    con.sql("""
        CREATE TABLE dcz AS
        SELECT dc.*, z.companies >= 3 AS in_batch
        FROM dc LEFT JOIN zipday z ON dc.has_zip5 AND dc.dt = z.dt AND dc.zip = z.zip
    """)

    # HUD ZIP->county. Allocate by residential share; fall back to total share
    # for ZIPs with no residential addresses.
    con.sql(f"""
        CREATE TABLE hud AS
        SELECT r.zip, r.geoid AS fips, r.res_ratio, r.tot_ratio
        FROM (SELECT unnest(data.results) AS r FROM read_json('{a.hud}', maximum_object_size=200000000))
    """)
    con.sql("""
        CREATE TABLE xw AS
        SELECT zip, fips,
               CASE WHEN sum(res_ratio) OVER (PARTITION BY zip) > 0 THEN res_ratio ELSE tot_ratio END AS w
        FROM hud
    """)
    con.sql("""
        CREATE TABLE county_year AS
        SELECT xw.fips, dcz.year,
               sum(w) AS complaints,
               sum(w) FILTER (NOT bureau) AS complaints_no_bureau,
               sum(w) FILTER (NOT coalesce(in_batch, false)) AS complaints_no_batch
        FROM dcz JOIN xw ON dcz.has_zip5 AND dcz.zip = xw.zip
        GROUP BY ALL
    """)
    con.sql("""
        CREATE TABLE county_zipdays AS
        SELECT xw.fips, year(z.dt) AS year, sum(w) AS zip_days
        FROM zipday z JOIN xw USING (zip) GROUP BY ALL
    """)

    # ACS 2020-2024 5-year. The API returns a JSON array of arrays, header first.
    con.sql(f"""
        CREATE TABLE acs AS
        WITH raw AS (SELECT unnest(j) AS r FROM (SELECT json(content)::VARCHAR[][] AS j
                     FROM read_text('{a.acs}')))
        SELECT r[7] || r[8] AS fips, r[1] AS name, r[7] AS state_fips,
               r[2]::INT AS pop, (r[4]::INT + r[5]::INT + r[6]::INT) AS pop_lt125
        FROM raw WHERE r[1] <> 'NAME'
    """)
    con.sql(f"""
        CREATE TABLE urban AS
        SELECT id AS fips, abbr, totcoll, medcoll, household_income_avg
        FROM read_csv('{a.urban}', nullstr='NA', types={{'id': 'VARCHAR', 'state_id': 'VARCHAR'}})
    """)

    lo, hi = PRE_SURGE
    con.sql(f"""
        CREATE TABLE county AS
        SELECT acs.fips, acs.name, acs.state_fips, acs.pop, acs.pop_lt125,
               round(100.0 * acs.pop_lt125 / acs.pop, 2) AS pct_lt125,
               u.abbr, u.totcoll, u.household_income_avg,
               coalesce(c25.complaints, 0) AS complaints_2025,
               1e4 * coalesce(c25.complaints, 0) / acs.pop AS rate_2025,
               1e4 * coalesce(c25.complaints_no_bureau, 0) / acs.pop AS rate_2025_no_bureau,
               1e4 * coalesce(c25.complaints_no_batch, 0) / acs.pop AS rate_2025_no_batch,
               1e4 * coalesce(z25.zip_days, 0) / acs.pop AS zipday_rate_2025,
               1e4 * coalesce(pre.complaints, 0) / {hi - lo + 1} / acs.pop AS rate_pre_surge
        FROM acs
        LEFT JOIN urban u USING (fips)
        LEFT JOIN (SELECT * FROM county_year WHERE year = 2025) c25 USING (fips)
        LEFT JOIN (SELECT * FROM county_zipdays WHERE year = 2025) z25 USING (fips)
        LEFT JOIN (SELECT fips, sum(complaints) AS complaints FROM county_year
                   WHERE year BETWEEN {lo} AND {hi} GROUP BY fips) pre USING (fips)
        WHERE acs.state_fips NOT IN ('72')  -- Urban covers the 50 states and DC
    """)


def write(con, sql: str, path: Path) -> None:
    con.sql(f"COPY ({sql}) TO '{path}' (HEADER, DELIMITER ',')")
    print(f"wrote {path}")


def surge(con, out: Path) -> None:
    write(con, """
        SELECT year, count(*) AS complaints,
               round(100 * avg((via = 'Web')::INT), 1) AS pct_web,
               round(100 * avg(bureau::INT), 1) AS pct_credit_bureaus,
               round(100 * avg((sub_product = 'I do not know')::INT), 1) AS pct_debt_type_unknown,
               round(100 * avg((issue = 'Attempts to collect debt not owed')::INT), 1) AS pct_not_owed,
               round(100 * avg((issue = 'Took or threatened to take negative or legal action')::INT), 1)
                   AS pct_legal_action,
               round(100 * avg(tags IS NOT NULL::INT), 1) AS pct_tagged,
               count(DISTINCT company) AS companies,
               round(100 * avg(in_batch::INT) FILTER (has_zip5), 1) AS pct_zip5_in_same_day_batch
        FROM dcz WHERE year BETWEEN 2017 AND 2026 GROUP BY year ORDER BY year
    """, out / "surge_by_year.csv")
    # ZIP-days are a rough count of filers: one person filing several complaints
    # on one day counts once. The placebo shows the chance rate of a second
    # complaint from the same ZIP, a week later.
    write(con, """
        SELECT year(a.dt) AS year, count(*) AS zip_days, sum(a.n) AS zip5_complaints,
               round(avg(a.n), 3) AS complaints_per_zip_day,
               round(avg(coalesce(b.n, 0)), 3) AS placebo_same_zip_week_later,
               round(100 * sum(a.n) FILTER (a.bureaus >= 2) / sum(a.n), 1) AS pct_in_2plus_bureau_batch
        FROM zipday a LEFT JOIN zipday b ON a.zip = b.zip AND b.dt = a.dt + 7
        WHERE year(a.dt) BETWEEN 2017 AND 2026 GROUP BY 1 ORDER BY 1
    """, out / "surge_zip_days.csv")
    yrs = """count(*) FILTER (year = 2021) AS n_2021, count(*) FILTER (year = 2023) AS n_2023,
             count(*) FILTER (year = 2025) AS n_2025"""
    write(con, f"""
        SELECT company, {yrs} FROM dc GROUP BY company ORDER BY n_2025 DESC LIMIT 25
    """, out / "surge_top_companies.csv")
    write(con, f"""
        SELECT 'issue' AS field, issue AS value, {yrs} FROM dc GROUP BY ALL
        UNION ALL SELECT 'sub_product', sub_product, {yrs} FROM dc GROUP BY ALL
        UNION ALL SELECT 'submitted_via', via, {yrs} FROM dc GROUP BY ALL
        ORDER BY field, n_2025 DESC
    """, out / "surge_mix.csv")


def national(con, out: Path) -> None:
    rows = []
    samples = {
        f"pop >= {MIN_POP:,}": f"pop >= {MIN_POP}",
        "all counties": "true",
    }
    pairs = [
        ("rate_2025", "totcoll", "2025 complaint rate vs. share with debt in collections"),
        ("rate_pre_surge", "totcoll", "2019-23 avg complaint rate vs. share with debt in collections"),
        ("rate_2025_no_bureau", "totcoll", "2025 rate excluding credit-bureau complaints vs. debt in collections"),
        ("rate_2025_no_batch", "totcoll", "2025 rate excluding same-day batches vs. debt in collections"),
        ("zipday_rate_2025", "totcoll", "2025 ZIP-days per 10K vs. debt in collections"),
        ("rate_2025", "pct_lt125", "2025 complaint rate vs. share under 125% of poverty"),
        ("totcoll", "pct_lt125", "debt in collections vs. share under 125% of poverty"),
        ("rate_2025", "household_income_avg", "2025 complaint rate vs. average household income"),
        ("rate_pre_surge", "rate_2025", "2019-23 complaint rate vs. 2025 complaint rate"),
    ]
    for label, where in samples.items():
        for x, y, desc in pairs:
            n, rho = con.sql(spearman("county", x, y, where)).fetchall()[0]
            rows.append((label, x, y, desc, n, rho))
        for x, y, desc in pairs[:5]:
            n, rho = con.sql(spearman_within_state("county", x, y, where)).fetchall()[0]
            rows.append((label + ", ranked within state", x, y, desc, n, rho))
    con.sql("CREATE TABLE nat_corr (sample VARCHAR, x VARCHAR, y VARCHAR, description VARCHAR, n INT, spearman DOUBLE)")
    con.executemany("INSERT INTO nat_corr VALUES (?, ?, ?, ?, ?, ?)", rows)
    write(con, "SELECT * FROM nat_corr", out / "national_correlations.csv")

    # Readable version: counties in tenths by debt in collections.
    write(con, f"""
        WITH c AS (SELECT *, ntile(10) OVER (ORDER BY totcoll) AS decile
                   FROM county WHERE pop >= {MIN_POP} AND totcoll IS NOT NULL)
        SELECT decile, count(*) AS counties,
               round(100 * min(totcoll), 1) AS min_pct_in_collections,
               round(100 * max(totcoll), 1) AS max_pct_in_collections,
               round(median(pct_lt125), 1) AS median_pct_lt125_poverty,
               round(median(rate_pre_surge), 2) AS median_rate_2019_23,
               round(median(rate_2025), 2) AS median_rate_2025,
               round(1e4 * sum(complaints_2025) / sum(pop), 2) AS pooled_rate_2025
        FROM c GROUP BY decile ORDER BY decile
    """, out / "national_by_collections_decile.csv")
    write(con, f"""
        SELECT abbr AS state, count(*) AS counties,
               round(100 * median(totcoll), 1) AS median_pct_in_collections,
               round(median(rate_2025), 2) AS median_rate_2025
        FROM county WHERE pop >= {MIN_POP} AND totcoll IS NOT NULL GROUP BY abbr ORDER BY abbr
    """, out / "national_by_state.csv")


def texas(con, a, out: Path) -> None:
    recs = read_tx(Path(a.tx))
    if not recs:
        print("no Texas court files found; skipping the Texas comparison")
        return
    con.sql("""CREATE TABLE tx_raw (county_name VARCHAR, year INT, reporting_pct DOUBLE,
               reports_received INT, reports_possible INT, debt_filed DOUBLE,
               debt_default DOUBLE, debt_disposed DOUBLE)""")
    con.executemany("INSERT INTO tx_raw VALUES (?, ?, ?, ?, ?, ?, ?, ?)", [
        (r.get("county_name"), r["year"], r.get("reporting_pct"), r.get("reports_received"),
         r.get("reports_possible"), r.get("debt_filed"),
         r.get("debt_default"), r.get("debt_disposed")) for r in recs])
    con.sql("""
        CREATE TABLE tx AS
        WITH t AS (PIVOT tx_raw ON year USING first(reporting_pct) AS rep, first(debt_filed) AS filed,
                   first(debt_default) AS dflt, first(debt_disposed) AS disposed GROUP BY county_name)
        SELECT c.*, t.*,
               1e3 * t."2025_filed" / c.pop AS filings_per_1k_2025,
               1e3 * t."2023_filed" / c.pop AS filings_per_1k_2023,
               round(100 * t."2025_dflt" / nullif(t."2025_disposed", 0), 1) AS pct_default_2025,
               1e4 * cy23.complaints / c.pop AS rate_2023
        FROM county c
        JOIN t ON norm_county(t.county_name) = norm_county(replace(split_part(c.name, ',', 1), ' County', ''))
        LEFT JOIN (SELECT * FROM county_year WHERE year = 2023) cy23 USING (fips)
        WHERE c.state_fips = '48'
    """)
    unmatched = con.sql("""SELECT DISTINCT county_name FROM tx_raw
                           WHERE county_name NOT IN (SELECT county_name FROM tx)""").fetchall()
    if unmatched:
        print("Texas counties that did not match ACS:", unmatched)

    write(con, """
        SELECT fips, county_name, pop, pct_lt125, round(100 * totcoll, 1) AS pct_in_collections,
               "2025_rep" AS reporting_pct_2025, "2025_filed" AS debt_filed_2025,
               round(filings_per_1k_2025, 2) AS debt_filings_per_1k_2025, pct_default_2025,
               round(complaints_2025, 1) AS complaints_2025, round(rate_2025, 2) AS complaints_per_10k_2025,
               "2023_rep" AS reporting_pct_2023, "2023_filed" AS debt_filed_2023,
               round(rate_2023, 2) AS complaints_per_10k_2023
        FROM tx ORDER BY pop DESC
    """, out / "texas_counties.csv")

    good25 = f'"2025_rep" >= {MIN_REPORTING}'
    good_both = f'{good25} AND "2023_rep" >= {MIN_REPORTING} AND "2023_filed" > 0 AND rate_2023 > 0'
    samples = {
        f"pop >= {MIN_POP:,}, reporting >= {MIN_REPORTING:.0f}%": f"pop >= {MIN_POP} AND {good25}",
        f"all counties, reporting >= {MIN_REPORTING:.0f}%": good25,
    }
    pairs = [
        ("rate_2025", "filings_per_1k_2025", "2025 complaint rate vs. 2025 debt-claim filing rate"),
        ("rate_pre_surge", "filings_per_1k_2025", "2019-23 complaint rate vs. 2025 debt-claim filing rate"),
        ("rate_2025_no_batch", "filings_per_1k_2025", "2025 rate excluding same-day batches vs. filing rate"),
        ("totcoll", "filings_per_1k_2025", "debt in collections vs. 2025 debt-claim filing rate"),
        ("rate_2025", "totcoll", "2025 complaint rate vs. debt in collections"),
        ("pct_lt125", "filings_per_1k_2025", "share under 125% of poverty vs. filing rate"),
    ]
    rows = []
    for label, where in samples.items():
        for x, y, desc in pairs:
            n, rho = con.sql(spearman("tx", x, y, where)).fetchall()[0]
            rows.append((label, x, y, desc, n, rho))
    # Change over time: do counties where filings grew also see complaints grow?
    con.sql("""CREATE TABLE tx_growth AS SELECT *, "2025_filed" / "2023_filed" AS filed_ratio,
               rate_2025 / rate_2023 AS complaint_ratio FROM tx""")
    for label, where in {f"pop >= {MIN_POP:,}, reporting >= {MIN_REPORTING:.0f}% both years":
                         f"pop >= {MIN_POP} AND {good_both}"}.items():
        n, rho = con.sql(spearman("tx_growth", "filed_ratio", "complaint_ratio", where)).fetchall()[0]
        rows.append((label, "filed_ratio", "complaint_ratio",
                     "2023->2025 growth in filings vs. growth in complaints", n, rho))
    con.sql("CREATE TABLE tx_corr (sample VARCHAR, x VARCHAR, y VARCHAR, description VARCHAR, n INT, spearman DOUBLE)")
    con.executemany("INSERT INTO tx_corr VALUES (?, ?, ?, ?, ?, ?)", rows)
    write(con, "SELECT * FROM tx_corr", out / "texas_correlations.csv")
    # Readable version: larger, fully reporting counties in thirds by poverty share.
    write(con, f"""
        WITH t AS (SELECT *, ntile(3) OVER (ORDER BY pct_lt125) AS poverty_third
                   FROM tx WHERE pop >= {MIN_POP} AND {good25})
        SELECT poverty_third, count(*) AS counties,
               round(median(pct_lt125), 1) AS median_pct_lt125_poverty,
               round(100 * median(totcoll), 1) AS median_pct_in_collections,
               round(median(filings_per_1k_2025), 1) AS median_debt_filings_per_1k_2025,
               round(median(pct_default_2025), 1) AS median_pct_default_2025,
               round(median(rate_2025), 1) AS median_complaints_per_10k_2025
        FROM t GROUP BY ALL ORDER BY poverty_third
    """, out / "texas_by_poverty_third.csv")
    write(con, f"""
        SELECT count(*) AS counties,
               count(*) FILTER ({good25}) AS counties_reporting_90pct_2025,
               sum(pop) FILTER ({good25}) / sum(pop) AS pop_share_reporting_90pct_2025,
               sum("2025_filed") AS debt_filed_2025, sum("2023_filed") AS debt_filed_2023,
               round(100 * sum("2025_dflt") / sum("2025_disposed"), 1) AS pct_default_2025,
               round(sum(complaints_2025), 0) AS complaints_2025
        FROM tx
    """, out / "texas_summary.csv")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--complaints", required=True)
    p.add_argument("--hud", required=True)
    p.add_argument("--urban", required=True)
    p.add_argument("--acs", required=True)
    p.add_argument("--tx", required=True)
    p.add_argument("--out", default="docs/phase0/need")
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    con.sql(NORM_COUNTY)
    build(con, a)
    surge(con, out)
    national(con, out)
    texas(con, a, out)


if __name__ == "__main__":
    main()
