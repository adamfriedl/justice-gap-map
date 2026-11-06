"""Phase 0: does LSC funding measure legal aid capacity?

Compares, by state, LSC's own funding with the total revenue of legal aid
nonprofits from the IRS Exempt Organizations Business Master File (BMF), all per
person under 125% of poverty (LSC's eligibility line).

    uv run python scripts/phase0_capacity.py \
        --bmf 'data/irs/2026-11-06/eo*.csv' \
        --lsc data/lsc/2026-11-06 \
        --acs data/acs/county_acs5_2024.json \
        --out docs/phase0/capacity

Inputs come from scripts/phase0_capacity_fetch.py and scripts/phase0_need_download.sh.
"""

import argparse
import html
import re
from pathlib import Path

import duckdb
import pypdf

# Legal-services NTEE codes. I80 is "Legal Services"; I83 is "Public Interest Law,
# Litigation", mostly impact litigation and advocacy rather than individual help,
# so it's reported separately as a sensitivity check.
NTEE_MAIN = "I80"
NTEE_SENSITIVITY = "I83"

# Non-grantee I80/I83 organizations that fund or coordinate legal aid rather than
# deliver it. Counting them would double-count money they regrant to providers.
# Matched on the BMF name, after LSC grantees are set aside.
FUNDER_RE = (r"BAR FOUNDATION|\bIOLTA\b|ACCESS TO JUSTICE|LEGAL AID NETWORK|FUND FOR JUSTICE"
             r"|LEGAL ASSISTANCE CORP|MASSACHUSETTS LEGAL ASSISTANCE|LEGAL SERVICES CORP\b|LAWYERS TRUST"
             r"|INTEREST ON LAWYERS|BAR ENDOWMENT"
             r"|LEGAL FOUNDATION OF|EQUAL JUSTICE (FUND|FOUNDATION|COALITION|PARTNERS)|LEGAL AID FUND")
# Public defenders and other criminal defense: not civil legal aid.
DEFENDER_RE = r"DEFENDER|INDIGENT PRISONERS|QUEENS LAW ASSOCIATES"


# LSC grantees whose BMF name differs from LSC's list (legal name or former name),
# matched by hand on name and city. Former-name matches are noted.
GRANTEE_EIN = {
    "Anishinabe Legal Services, Inc.": "410960032",
    "Appalachian Research and Defense Fund of Kentucky": "610848948",
    "Essex-Newark Legal Services Project, Inc.": "221779177",
    "Idaho Legal Aid Services, Inc.": "820293641",
    "Northwestern Legal Services": "251201331",
    "Texas RioGrande Legal Aid, Inc.": "741675230",
    "Land of Lincoln Legal Aid, Inc.": "370958448",  # BMF: Land of Lincoln Legal Assistance Foundation
    "Maryland Legal Aid": "520591621",  # BMF: Legal Aid Bureau Inc (former name)
    "Justice North": "410958386",  # BMF: Legal Aid Service of Northeastern Minnesota (former name)
    "Legal Services Vermont": "030349316",  # BMF: Legal Services Law Line of Vermont (former name)
    "Legal Aid of the Bluegrass": "610668572",  # BMF: Northern Kentucky Legal Aid Society (former name)
}

# Normalize organization names for matching: upper case, punctuation and legal
# suffixes (Inc, Corp, ...) dropped, "&" spelled out.
NORM_NAME = r"""
CREATE MACRO norm_name(s) AS trim(regexp_replace(regexp_replace(regexp_replace(
    replace(upper(s), '&', ' AND '), '[^A-Z0-9 ]', ' ', 'g'),
    '\b(INC|INCORPORATED|THE|OF|CORP|CORPORATION|CO|LLC)\b', ' ', 'g'), ' +', ' ', 'g'))
"""


def parse_grantees(page: str) -> list[tuple[str, str]]:
    """(state name, grantee name) pairs from https://www.lsc.gov/about-lsc/our-grantees."""
    out = []
    items = re.split(r'<div class="accordion accordion--collapsed', page)[1:]
    for item in items:
        state = re.search(r'field--name-field-plain-title[^>]*>([^<]+)<', item)
        body = re.search(r'accordion__content.*?<ul>(.*?)</ul>', item, re.S)
        if not (state and body):
            continue
        for name in re.findall(r"<li>(?:<a[^>]*>)?([^<]+)", body.group(1)):
            out.append((html.unescape(state.group(1)).strip(), html.unescape(name).strip()))
    return out


def parse_profile(text: str) -> dict:
    """LSC funding and year from one LSC state profile (one-page PDF)."""
    out = {}
    if m := re.search(r"\$([\d,]+)\s*\n\s*to serve the eligible population", text):
        out["lsc_funding"] = int(m.group(1).replace(",", ""))
    if m := re.search(r"FUNDING IN (\d{4})", text):
        out["lsc_funding_year"] = int(m.group(1))
    if m := re.search(r"\n([A-Z][A-Za-z. ]+)\n1 in \d+ people", text):
        out["state_name"] = m.group(1).strip()
    return out


def write(con, sql: str, path: Path) -> None:
    con.sql(f"COPY ({sql}) TO '{path}' (HEADER, DELIMITER ',')")
    print(f"wrote {path}")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--bmf", required=True, help="glob for the BMF eo*.csv files")
    p.add_argument("--lsc", required=True)
    p.add_argument("--acs", required=True)
    p.add_argument("--out", default="docs/phase0/capacity")
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    lsc = Path(a.lsc)
    con = duckdb.connect()
    con.sql(NORM_NAME)

    # LSC state profiles: LSC funding per state.
    rows = []
    for pdf in sorted((lsc / "state_profiles").glob("*.pdf")):
        text = "\n".join(pg.extract_text() or "" for pg in pypdf.PdfReader(pdf).pages)
        r = parse_profile(text)
        rows.append((pdf.stem, r.get("state_name"), r.get("lsc_funding"), r.get("lsc_funding_year")))
    con.sql("CREATE TABLE profile (state_fips VARCHAR, state_name VARCHAR, lsc_funding BIGINT, lsc_funding_year INT)")
    con.executemany("INSERT INTO profile VALUES (?, ?, ?, ?)", rows)

    # LSC grantee list.
    grantees = parse_grantees((lsc / "our-grantees.html").read_text(errors="ignore"))
    con.sql("CREATE TABLE grantee (state_name VARCHAR, grantee VARCHAR)")
    con.executemany("INSERT INTO grantee VALUES (?, ?)", grantees)

    # ACS: population under 125% of poverty, by state.
    con.sql(f"""
        CREATE TABLE acs_state AS
        WITH raw AS (SELECT unnest(j) AS r FROM (SELECT json(content)::VARCHAR[][] AS j FROM read_text('{a.acs}')))
        SELECT r[7] AS state_fips, sum(r[2]::BIGINT) AS pop,
               sum(r[4]::BIGINT + r[5]::BIGINT + r[6]::BIGINT) AS pop_lt125
        FROM raw WHERE r[1] <> 'NAME' GROUP BY 1
    """)

    con.sql(f"""
        CREATE TABLE bmf AS
        SELECT EIN AS ein, NAME AS name, norm_name(NAME) AS nname, CITY AS city, STATE AS state,
               NTEE_CD AS ntee, TAX_PERIOD AS tax_period, TRY_CAST(REVENUE_AMT AS BIGINT) AS revenue
        FROM read_csv('{a.bmf}', all_varchar=true, header=true)
    """)
    con.sql("CREATE TABLE alias (grantee VARCHAR, ein VARCHAR)")
    con.executemany("INSERT INTO alias VALUES (?, ?)", list(GRANTEE_EIN.items()))
    # Match each grantee to the BMF by normalized name, any NTEE code; when a name
    # appears more than once, take the record with the most revenue.
    con.sql("""
        CREATE TABLE grantee_bmf AS
        WITH g AS (SELECT DISTINCT grantee, norm_name(grantee) AS nname FROM grantee)
        SELECT g.grantee, b.ein, b.name, b.city, b.state, b.ntee, b.tax_period, b.revenue,
               a.ein IS NOT NULL AS matched_by_hand
        FROM g
        LEFT JOIN alias a USING (grantee)
        LEFT JOIN (
            SELECT *, row_number() OVER (PARTITION BY nname ORDER BY revenue DESC NULLS LAST) AS rn FROM bmf
        ) b ON (a.ein IS NULL AND b.nname = g.nname AND b.rn = 1) OR b.ein = a.ein
    """)
    write(con, "SELECT * FROM grantee_bmf ORDER BY ein IS NULL DESC, grantee", out / "lsc_grantees_bmf_match.csv")

    con.sql(f"""
        CREATE TABLE orgs AS
        SELECT b.*,
            CASE WHEN b.ein IN (SELECT ein FROM grantee_bmf WHERE ein IS NOT NULL) THEN 'lsc_grantee'
                 WHEN b.name = 'LEGAL SERVICES CORPORATION' THEN 'excluded_lsc_itself'
                 WHEN regexp_matches(b.name, '{DEFENDER_RE}') THEN 'excluded_defender'
                 WHEN regexp_matches(b.name, '{FUNDER_RE}') THEN 'excluded_funder'
                 WHEN b.ntee LIKE '{NTEE_MAIN}%' THEN 'other_i80'
                 WHEN b.ntee LIKE '{NTEE_SENSITIVITY}%' THEN 'other_i83'
            END AS role
        FROM bmf b
        WHERE b.ntee LIKE 'I8%' OR b.ein IN (SELECT ein FROM grantee_bmf WHERE ein IS NOT NULL)
    """)
    write(con, """
        SELECT role, count(*) AS orgs, count(revenue) AS with_revenue,
               round(sum(revenue) / 1e6, 1) AS revenue_millions,
               count(*) FILTER (revenue >= 1e6) AS orgs_1m_plus
        FROM orgs GROUP BY role ORDER BY revenue_millions DESC
    """, out / "bmf_roles.csv")
    write(con, """
        SELECT role, name, city, state, ntee, tax_period, revenue FROM orgs
        WHERE role LIKE 'excluded%' AND revenue >= 1e6 ORDER BY revenue DESC
    """, out / "bmf_excluded_1m_plus.csv")

    con.sql("""
        CREATE TABLE state AS
        WITH r AS (
            SELECT state,
                   sum(revenue) FILTER (role = 'lsc_grantee') AS grantee_rev,
                   sum(revenue) FILTER (role = 'other_i80') AS other_i80_rev,
                   sum(revenue) FILTER (role = 'other_i83') AS other_i83_rev,
                   count(*) FILTER (role IN ('lsc_grantee', 'other_i80') AND revenue > 0) AS providers
            FROM orgs GROUP BY state),
        top AS (
            SELECT state, max(revenue) AS top_rev, arg_max(name, revenue) AS top_org
            FROM orgs WHERE role IN ('lsc_grantee', 'other_i80') GROUP BY state)
        SELECT p.state_fips, p.state_name, a.pop_lt125, p.lsc_funding, p.lsc_funding_year,
               coalesce(r.grantee_rev, 0) AS lsc_grantee_revenue,
               coalesce(r.other_i80_rev, 0) AS other_i80_revenue,
               coalesce(r.other_i83_rev, 0) AS other_i83_revenue,
               coalesce(r.grantee_rev, 0) + coalesce(r.other_i80_rev, 0) AS provider_revenue,
               r.providers, top.top_org, top.top_rev
        FROM profile p
        JOIN acs_state a USING (state_fips)
        LEFT JOIN (SELECT DISTINCT state_fips, state FROM (VALUES
            ('01','AL'),('02','AK'),('04','AZ'),('05','AR'),('06','CA'),('08','CO'),('09','CT'),('10','DE'),
            ('11','DC'),('12','FL'),('13','GA'),('15','HI'),('16','ID'),('17','IL'),('18','IN'),('19','IA'),
            ('20','KS'),('21','KY'),('22','LA'),('23','ME'),('24','MD'),('25','MA'),('26','MI'),('27','MN'),
            ('28','MS'),('29','MO'),('30','MT'),('31','NE'),('32','NV'),('33','NH'),('34','NJ'),('35','NM'),
            ('36','NY'),('37','NC'),('38','ND'),('39','OH'),('40','OK'),('41','OR'),('42','PA'),('44','RI'),
            ('45','SC'),('46','SD'),('47','TN'),('48','TX'),('49','UT'),('50','VT'),('51','VA'),('53','WA'),
            ('54','WV'),('55','WI'),('56','WY'),('72','PR')) AS s(state_fips, state)) s USING (state_fips)
        LEFT JOIN r USING (state)
        LEFT JOIN top USING (state)
    """)
    write(con, """
        SELECT state_fips, state_name, pop_lt125, lsc_funding, lsc_funding_year,
               round(lsc_funding / pop_lt125, 2) AS lsc_per_eligible,
               lsc_grantee_revenue, round(lsc_grantee_revenue / pop_lt125, 2) AS lsc_grantee_rev_per_eligible,
               other_i80_revenue, provider_revenue,
               round(provider_revenue / pop_lt125, 2) AS provider_rev_per_eligible,
               round(provider_revenue / lsc_funding, 1) AS provider_rev_to_lsc,
               other_i83_revenue, providers, top_org,
               round(100 * top_rev / nullif(provider_revenue, 0), 1) AS pct_in_largest_org
        FROM state ORDER BY provider_rev_per_eligible DESC
    """, out / "state_capacity.csv")

    def rho(x, y):
        return con.sql(f"""
            SELECT count(*), round(corr(rx, ry), 3) FROM (
              SELECT rank() OVER (ORDER BY {x}) AS rx, rank() OVER (ORDER BY {y}) AS ry
              FROM state WHERE {x} IS NOT NULL AND {y} IS NOT NULL AND {y} > 0)
        """).fetchall()[0]

    stats = [
        ("lsc_per_eligible vs provider_rev_per_eligible (Spearman)",
         *rho("lsc_funding / pop_lt125", "provider_revenue / pop_lt125")),
        ("lsc_per_eligible vs lsc_grantee_rev_per_eligible (Spearman)",
         *rho("lsc_funding / pop_lt125", "lsc_grantee_revenue / pop_lt125")),
    ]
    for label, col in [("lsc_per_eligible", "lsc_funding / pop_lt125"),
                       ("lsc_grantee_rev_per_eligible", "lsc_grantee_revenue / pop_lt125"),
                       ("provider_rev_per_eligible", "provider_revenue / pop_lt125")]:
        q = con.sql(f"""SELECT count(*), round(min({col}), 2), round(quantile_cont({col}, 0.1), 2),
                               round(median({col}), 2), round(quantile_cont({col}, 0.9), 2), round(max({col}), 2)
                        FROM state WHERE {col} > 0""").fetchall()[0]
        stats.append((f"{label}: n, min, p10, median, p90, max", q[0], ", ".join(str(v) for v in q[1:])))
    totals = con.sql("""SELECT sum(lsc_funding), sum(lsc_grantee_revenue), sum(provider_revenue) FROM state""").fetchall()[0]
    stats.append(("sum of LSC state-profile funding", None, str(totals[0])))
    stats.append(("sum of LSC grantee revenue in BMF (states in profiles)", None, str(totals[1])))
    stats.append(("sum of provider revenue in BMF (states in profiles)", None, str(totals[2])))
    con.sql("CREATE TABLE stats (stat VARCHAR, n INT, value VARCHAR)")
    con.executemany("INSERT INTO stats VALUES (?, ?, ?)", [(s, n, str(v)) for s, n, v in stats])
    write(con, "SELECT * FROM stats", out / "capacity_summary.csv")


if __name__ == "__main__":
    main()
