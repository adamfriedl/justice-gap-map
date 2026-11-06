"""Phase 0: how well can debt-collection complaints be placed geographically?

Reads the CFPB complaints CSV (or a Parquet copy of it) and the HUD ZIP->county
crosswalk JSON, then writes summary CSVs to an output directory.

    uv run python scripts/phase0_cfpb_zip.py \
        --complaints data/cfpb/2026-11-06/complaints.csv \
        --hud data/hud/zip_county_20262.json \
        --out docs/phase0

ZIP classes follow the CFPB field reference
(https://cfpb.github.io/api/ccdb/fields.html): a 5-digit ZIP, a 3-digit ZIP
published as "123XX", or nothing usable (blank, "XXXXX", or malformed).
"""

import argparse
from pathlib import Path

import duckdb

PRODUCT = "Debt collection"

# One CASE expression, shared with the tests so the rules live in one place.
ZIP_CLASS_SQL = """
CASE
    WHEN regexp_full_match(coalesce(zip, ''), '[0-9]{5}') THEN 'zip5'
    WHEN regexp_full_match(coalesce(zip, ''), '[0-9]{3}XX') THEN 'zip3'
    ELSE 'none'
END
"""


def source_sql(path: str) -> str:
    if path.endswith(".parquet"):
        return f"read_parquet('{path}')"
    return f"read_csv('{path}', all_varchar=true, header=true)"


def build(con: duckdb.DuckDBPyConnection, complaints: str, hud: str) -> None:
    con.sql(f"""
        CREATE TABLE dc AS
        SELECT
            "Complaint ID" AS complaint_id,
            year(CAST("Date received" AS DATE)) AS year,
            coalesce(nullif(State, ''), '(blank)') AS state,
            "ZIP code" AS zip
        FROM {source_sql(complaints)}
        WHERE Product = '{PRODUCT}'
    """)
    con.sql("ALTER TABLE dc ADD COLUMN zip_class VARCHAR")
    con.sql(f"UPDATE dc SET zip_class = {ZIP_CLASS_SQL}")

    # HUD API response: {"data": {"year", "quarter", "results": [...]}}
    con.sql(f"""
        CREATE TABLE hud AS
        SELECT r.zip, r.geoid AS county, r.state AS hud_state,
               r.res_ratio, r.tot_ratio
        FROM (SELECT unnest(data.results) AS r FROM read_json('{hud}', maximum_object_size=200000000))
    """)
    con.sql("""
        CREATE TABLE hud_zip AS
        SELECT zip, count(*) AS n_counties, max(res_ratio) AS top_res_ratio,
               sum(res_ratio) = 0 AS no_residential,
               list(DISTINCT hud_state) AS hud_states
        FROM hud GROUP BY zip
    """)
    con.sql("""
        CREATE TABLE hud_zip3 AS
        SELECT left(zip, 3) AS zip3, count(DISTINCT county) AS n_counties
        FROM hud GROUP BY 1
    """)
    con.sql("""
        CREATE TABLE placed AS
        SELECT dc.*,
            CASE
                WHEN zip_class = 'zip5' AND h.zip IS NOT NULL THEN 'zip5_matched'
                WHEN zip_class = 'zip5' THEN 'zip5_unmatched'
                ELSE zip_class
            END AS placement,
            h.n_counties AS zip5_counties,
            h.top_res_ratio,
            h.no_residential,
            NOT list_contains(h.hud_states, dc.state) AS state_mismatch,
            h3.n_counties AS zip3_counties
        FROM dc
        LEFT JOIN hud_zip h ON zip_class = 'zip5' AND dc.zip = h.zip
        LEFT JOIN hud_zip3 h3 ON zip_class = 'zip3' AND left(dc.zip, 3) = h3.zip3
    """)


SHARES = """
    count(*) AS complaints,
    round(100 * avg((zip_class = 'zip5')::INT), 2) AS pct_zip5,
    round(100 * avg((zip_class = 'zip3')::INT), 2) AS pct_zip3,
    round(100 * avg((zip_class = 'none')::INT), 2) AS pct_none,
    round(100 * avg((placement = 'zip5_matched')::INT), 2) AS pct_county_placeable
"""


def write(con, sql: str, path: Path) -> None:
    con.sql(f"COPY ({sql}) TO '{path}' (HEADER, DELIMITER ',')")
    print(f"wrote {path}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--complaints", required=True)
    p.add_argument("--hud", required=True)
    p.add_argument("--out", default="docs/phase0")
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    con = duckdb.connect()
    build(con, a.complaints, a.hud)

    write(con, f"SELECT 'all' AS scope, {SHARES} FROM placed", out / "zip_class_overall.csv")
    write(con, f"SELECT state, {SHARES} FROM placed GROUP BY state ORDER BY complaints DESC",
          out / "zip_class_by_state.csv")
    write(con, f"SELECT year, {SHARES} FROM placed GROUP BY year ORDER BY year",
          out / "zip_class_by_year.csv")
    write(con, f"SELECT state, year, {SHARES} FROM placed GROUP BY ALL ORDER BY state, year",
          out / "zip_class_by_state_year.csv")

    # Crosswalk match, by distinct ZIP and by complaint, overall and by year.
    match = """
        count(DISTINCT zip) FILTER (zip_class = 'zip5') AS distinct_zip5,
        count(DISTINCT zip) FILTER (placement = 'zip5_matched') AS distinct_zip5_matched,
        round(100 * distinct_zip5_matched / distinct_zip5, 2) AS pct_distinct_matched,
        count(*) FILTER (zip_class = 'zip5') AS zip5_complaints,
        count(*) FILTER (placement = 'zip5_matched') AS zip5_complaints_matched,
        round(100 * zip5_complaints_matched / zip5_complaints, 2) AS pct_complaints_matched,
        round(100 * avg((zip5_counties = 1)::INT) FILTER (placement = 'zip5_matched'), 2)
            AS pct_matched_in_single_county_zip,
        round(100 * avg((top_res_ratio >= 0.9)::INT) FILTER (placement = 'zip5_matched'), 2)
            AS pct_matched_90pct_one_county,
        count(*) FILTER (no_residential) AS matched_complaints_no_residential_addr,
        round(100 * avg(state_mismatch::INT) FILTER (placement = 'zip5_matched'), 2)
            AS pct_matched_state_mismatch,
        round(100 * avg((zip3_counties = 1)::INT) FILTER (zip_class = 'zip3'), 2)
            AS pct_zip3_in_single_county_prefix
    """
    write(con, f"SELECT 'all' AS scope, {match} FROM placed", out / "crosswalk_match_overall.csv")
    write(con, f"SELECT year, {match} FROM placed GROUP BY year ORDER BY year",
          out / "crosswalk_match_by_year.csv")
    write(con, """
        SELECT zip, count(*) AS complaints, min(year) AS first_year, max(year) AS last_year,
               string_agg(DISTINCT state, ' ') AS states
        FROM placed WHERE placement = 'zip5_unmatched'
        GROUP BY zip ORDER BY complaints DESC LIMIT 30
    """, out / "crosswalk_unmatched_top_zips.csv")


if __name__ == "__main__":
    main()
