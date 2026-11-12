"""The Harris County debt docket: who files debt claims, for how much, and how
the cases end.

Reads the case-level extracts written by scripts/lawsuits_fetch_harris.py (or
the daily job, src/ingest_harris.py), which hold no defendant names or
addresses. Writes small aggregate tables to docs/docket/.

    uv run python scripts/docket.py --data data/harris --out docs/docket

How cases are counted:
- The extract has one row per case and party. Rows are collapsed to one per
  case number.
- A case can appear in several snapshots (data/harris/<download date>/). The
  rows from the latest download are used, so each case shows its latest status.
- Outcomes are reported for cases filed in one year (--cohort), all at least
  ten months old, as shares of all cases filed. Newer cases are mostly open.

Plaintiff names: the same company is typed many ways ("LVNV Funding, LLC",
"Lvnv Funding Llc"). clean_plaintiff() reduces a name to a key: upper case, no
punctuation, nothing after "assignee of" and similar phrases, no company
suffix. docs/docket/plaintiff_names.csv then maps keys to a display name and a
kind of plaintiff, and fixes misspellings. Keys not in that file keep their own
name and the kind "other or not classified".
"""

import argparse
import csv
import re
from pathlib import Path

import duckdb

NAMES = Path("docs/docket/plaintiff_names.csv")
MIN_ZIP_CASES = 50  # ZIP codes with fewer cases are left out of the ZIP table
# The ZIP table has no outcome columns on purpose: how fast cases close differs
# a lot between the 16 courts, and a ZIP's cases mostly go to one court, so ZIP
# outcome rates would mostly show the court.

# Text after these phrases names someone else (the original lender, a trade
# name), not the company that filed the case.
CUT = re.compile(
    r"\s+(AS\s+)?(ASSIGNEE\s*OF|SUCCESSOR\s+BY\s+MERGER\s+TO|SUCCESSOR\s+IN\s+INTEREST\s+TO|"
    r"TRUST\s+MANAGER\s+FOR|DBA)\b.*$")
SUFFIX = re.compile(r"(\s+(LLC|L L C|INC|INCORPORATED|NA|CORP|CORPORATION|LTD|LP|CO|COMPANY|NATIONAL ASSOCIATION))+$")


def clean_plaintiff(name: str) -> str:
    s = re.sub(r"[^A-Z0-9 ]", " ", (name or "").upper().replace("D/B/A", " DBA ").replace("&", " AND "))
    s = re.sub(r"\s+", " ", s).strip()
    s = re.sub(r"\bN A\b", "NA", s)
    s = CUT.sub("", s)
    kept = SUFFIX.sub("", s)
    # "Sun Loan Company" should not become "Sun Loan"... but "Tower Loan Co" should
    # match "Tower Loan". Suffixes go; a name that is only a suffix stays.
    return kept or s


def load_names(path: Path = NAMES) -> dict[str, tuple[str, str]]:
    with path.open() as f:
        return {r["key"]: (r["name"], r["kind"]) for r in csv.DictReader(f)}


def display(key: str, names: dict) -> tuple[str, str]:
    if key in names:
        return names[key]
    return (key.title() if key else "(blank)", "other or not classified")


def build(con, data: str, names: dict) -> None:
    """Tables: cases (one row per case, latest snapshot) with plaintiff and kind."""
    con.sql(f"""
        CREATE TABLE rows AS
        SELECT *, regexp_extract(filename, '(\\d{{4}}-\\d{{2}}-\\d{{2}})[/\\\\][^/\\\\]+$', 1) AS snapshot
        FROM read_csv('{data}/*/*.csv', all_varchar=true, filename=true)
    """)
    raw = [r[0] for r in con.sql('SELECT DISTINCT "Plaintiff Name" FROM rows').fetchall()]
    con.sql("CREATE TABLE plaintiff (raw VARCHAR, plaintiff VARCHAR, kind VARCHAR)")
    con.executemany("INSERT INTO plaintiff VALUES (?, ?, ?)",
                    [(r, *display(clean_plaintiff(r or ""), names)) for r in raw])
    con.sql("""
        CREATE TABLE cases AS
        WITH latest AS (
            SELECT * FROM rows QUALIFY snapshot = max(snapshot) OVER (PARTITION BY "Case Number"))
        SELECT "Case Number" AS case_number,
               any_value(snapshot) AS snapshot,
               strptime(any_value("Case File Date"), '%m/%d/%Y')::DATE AS filed,
               any_value("JP Court ID") AS court,
               any_value(p.plaintiff) AS plaintiff, any_value(p.kind) AS kind,
               any_value("Plaintiff Atty Name") AS plaintiff_attorney,
               try_cast(any_value("Claim Amount") AS DOUBLE) AS claim,
               nullif(any_value("Defendant Addr Zip"), '') AS zip,
               bool_or("Defendant Has Attorney" = 'Y') AS defendant_attorney,
               CASE WHEN any_value("Disposition Desc") IS NULL OR any_value("Disposition Desc") = '' THEN 'open'
                    WHEN any_value("Disposition Desc") LIKE 'Default Judgment%' THEN 'default judgment'
                    WHEN any_value("Disposition Desc") LIKE 'Non-suited%' THEN 'dropped by plaintiff'
                    WHEN any_value("Disposition Desc") LIKE 'Agreed Judgment%' THEN 'agreed judgment'
                    WHEN any_value("Disposition Desc") LIKE 'Dismissed for Want%' THEN 'dismissed, plaintiff did not pursue'
                    WHEN any_value("Disposition Desc") LIKE 'Trial%' THEN 'trial'
                    ELSE 'other' END AS outcome
        FROM latest l LEFT JOIN plaintiff p ON p.raw IS NOT DISTINCT FROM l."Plaintiff Name"
        GROUP BY 1
    """)


OUTCOME_COLS = """
    round(100.0 * count(*) FILTER (outcome = 'default judgment') / count(*), 1) AS pct_default_judgment,
    round(100.0 * count(*) FILTER (outcome = 'dropped by plaintiff') / count(*), 1) AS pct_dropped_by_plaintiff,
    round(100.0 * count(*) FILTER (outcome = 'agreed judgment') / count(*), 1) AS pct_agreed_judgment,
    round(100.0 * count(*) FILTER (outcome = 'dismissed, plaintiff did not pursue') / count(*), 1) AS pct_dismissed_not_pursued,
    round(100.0 * count(*) FILTER (outcome IN ('trial', 'other')) / count(*), 1) AS pct_trial_or_other,
    round(100.0 * count(*) FILTER (outcome = 'open') / count(*), 1) AS pct_open
"""
ATTORNEY_COL = "round(100.0 * count(*) FILTER (defendant_attorney) / count(*), 1) AS pct_defendant_had_attorney"


def write(con, sql: str, path: Path) -> None:
    con.sql(f"COPY ({sql}) TO '{path}' (HEADER, DELIMITER ',')")
    print(f"wrote {path}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="data/harris")
    p.add_argument("--out", default="docs/docket")
    p.add_argument("--cohort", type=int, default=2025, help="filing year for the outcome tables")
    p.add_argument("--top", type=int, default=40)
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    con = duckdb.connect()
    build(con, a.data, load_names())
    y = a.cohort
    cohort = f"year(filed) = {y}"

    write(con, f"""
        SELECT * FROM (VALUES
          ('snapshot (latest download date)', (SELECT max(snapshot) FROM cases)),
          ('first filing date', (SELECT min(filed)::VARCHAR FROM cases)),
          ('last filing date', (SELECT max(filed)::VARCHAR FROM cases)),
          ('rows in the extracts', (SELECT count(*)::VARCHAR FROM rows)),
          ('cases', (SELECT count(*)::VARCHAR FROM cases)),
          ('cases filed in {y}', (SELECT count(*)::VARCHAR FROM cases WHERE {cohort})),
          ('plaintiffs after name cleaning', (SELECT count(DISTINCT plaintiff)::VARCHAR FROM cases)),
          ('plaintiff names as typed', (SELECT count(*)::VARCHAR FROM plaintiff)),
          ('share of cases filed by the 10 largest plaintiffs, percent', (
              SELECT round(100.0 * sum(n) / (SELECT count(*) FROM cases), 1)::VARCHAR
              FROM (SELECT count(*) n FROM cases GROUP BY plaintiff ORDER BY n DESC LIMIT 10))),
          ('share of cases filed by debt buyers, percent', (
              SELECT round(100.0 * count(*) FILTER (kind = 'debt buyer') / count(*), 1)::VARCHAR FROM cases)),
          ('share of cases whose plaintiff is not classified, percent', (
              SELECT round(100.0 * count(*) FILTER (kind = 'other or not classified') / count(*), 1)::VARCHAR FROM cases)),
          ('median claim, dollars', (SELECT round(median(claim))::BIGINT::VARCHAR FROM cases WHERE claim > 0)),
          ('total claimed, dollars', (SELECT round(sum(claim))::BIGINT::VARCHAR FROM cases WHERE claim > 0)),
          ('total claimed in cases filed in {y}, dollars', (
              SELECT round(sum(claim))::BIGINT::VARCHAR FROM cases WHERE claim > 0 AND {cohort})),
          ('cases with no claim amount', (SELECT count(*)::VARCHAR FROM cases WHERE claim IS NULL OR claim <= 0)),
          ('plaintiff attorneys named', (SELECT count(DISTINCT plaintiff_attorney)::VARCHAR FROM cases WHERE plaintiff_attorney <> '')),
          ('share of cases filed by the 5 busiest plaintiff attorneys, percent', (
              SELECT round(100.0 * sum(n) / (SELECT count(*) FROM cases), 1)::VARCHAR
              FROM (SELECT count(*) n FROM cases WHERE plaintiff_attorney <> '' GROUP BY plaintiff_attorney ORDER BY n DESC LIMIT 5)))
        ) AS t(measure, value)
    """, out / "summary.csv")

    write(con, f"""
        WITH top AS (SELECT plaintiff FROM cases GROUP BY 1 ORDER BY count(*) DESC, 1 LIMIT {a.top}),
             c AS (SELECT *, CASE WHEN plaintiff IN (SELECT plaintiff FROM top) THEN plaintiff
                                  ELSE 'All other plaintiffs' END AS p,
                          CASE WHEN plaintiff IN (SELECT plaintiff FROM top) THEN kind ELSE '' END AS k FROM cases)
        SELECT p AS plaintiff, any_value(k) AS kind, count(*) AS cases,
               round(100.0 * count(*) / (SELECT count(*) FROM cases), 1) AS pct_of_cases,
               count(*) FILTER ({cohort}) AS cases_{y},
               count(*) FILTER (year(filed) = {y + 1}) AS cases_{y + 1}_to_date,
               round(median(claim) FILTER (claim > 0))::BIGINT AS median_claim,
               round(sum(claim) FILTER (claim > 0))::BIGINT AS total_claimed
        FROM c GROUP BY p ORDER BY (p = 'All other plaintiffs'), cases DESC
    """, out / "by_plaintiff.csv")

    write(con, f"""
        WITH top AS (SELECT plaintiff FROM cases GROUP BY 1 ORDER BY count(*) DESC, 1 LIMIT {a.top}),
             c AS (SELECT *, CASE WHEN plaintiff IN (SELECT plaintiff FROM top) THEN plaintiff
                                  ELSE 'All other plaintiffs' END AS p FROM cases WHERE {cohort})
        SELECT p AS plaintiff, count(*) AS cases_{y}, {OUTCOME_COLS}, {ATTORNEY_COL}
        FROM c GROUP BY p HAVING count(*) >= 100 ORDER BY (p = 'All other plaintiffs'), cases_{y} DESC
    """, out / f"outcomes_by_plaintiff_{y}.csv")

    write(con, f"SELECT kind, count(*) AS cases_{y}, round(median(claim) FILTER (claim > 0))::BIGINT AS median_claim, {OUTCOME_COLS}, {ATTORNEY_COL} FROM cases WHERE {cohort} GROUP BY kind ORDER BY 2 DESC",
          out / f"outcomes_by_kind_{y}.csv")

    write(con, f"""
        SELECT CASE WHEN defendant_attorney THEN 'defendant had an attorney' ELSE 'no attorney recorded' END AS group_name,
               count(*) AS cases_{y}, {OUTCOME_COLS}
        FROM cases WHERE {cohort} GROUP BY 1 ORDER BY 1
    """, out / f"outcomes_by_representation_{y}.csv")

    write(con, """
        SELECT strftime(filed, '%Y-%m') AS month, count(*) AS cases,
               count(*) FILTER (kind = 'debt buyer') AS debt_buyer,
               count(*) FILTER (kind = 'bank or card issuer') AS bank_or_card_issuer,
               count(*) FILTER (kind IN ('consumer lender', 'auto lender')) AS lender,
               count(*) FILTER (kind = 'other or not classified') AS other_or_not_classified,
               round(median(claim) FILTER (claim > 0))::BIGINT AS median_claim
        FROM cases GROUP BY 1 ORDER BY 1
    """, out / "by_month.csv")

    write(con, f"SELECT court, count(*) AS cases_{y}, {OUTCOME_COLS}, {ATTORNEY_COL} FROM cases WHERE {cohort} GROUP BY court ORDER BY 2 DESC",
          out / f"by_court_{y}.csv")

    write(con, f"""
        SELECT zip, count(*) AS cases_{y},
               round(100.0 * count(*) FILTER (outcome = 'open') / count(*), 1) AS pct_open, {ATTORNEY_COL}
        FROM cases WHERE {cohort} AND zip IS NOT NULL GROUP BY zip HAVING count(*) >= {MIN_ZIP_CASES} ORDER BY 2 DESC
    """, out / f"by_zip_{y}.csv")

    # For the maintainer: the largest names the lookup doesn't cover yet.
    print(con.sql("""SELECT plaintiff, count(*) n FROM cases WHERE kind = 'other or not classified'
                     GROUP BY 1 ORDER BY 2 DESC LIMIT 25""").fetchall())


if __name__ == "__main__":
    main()
