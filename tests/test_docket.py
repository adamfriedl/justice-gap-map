import csv
import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from docket import build, clean_plaintiff, display, load_names  # noqa: E402
from lawsuits_fetch_harris import KEEP  # noqa: E402


def test_clean_plaintiff_merges_the_ways_one_company_is_typed():
    for typed in ["LVNV Funding, LLC", "Lvnv Funding Llc", "LVNV FUNDING LLC,", "LVNV Funding LLC as assignee of Vion Holdings LLC"]:
        assert clean_plaintiff(typed) == "LVNV FUNDING"
    for typed in ["Bank of America, N.A.", "Bank Of America N.a.", "BANK OF AMERICA N A", "Bank of America NA"]:
        assert clean_plaintiff(typed) == "BANK OF AMERICA"
    assert clean_plaintiff("Capital One, N.a., Successor By Merger To Discover Bank") == "CAPITAL ONE"
    assert clean_plaintiff("Carmax Business Services, Llc D/b/a Carmax Auto Finance") == "CARMAX BUSINESS SERVICES"
    assert clean_plaintiff("US Bank National Association") == "US BANK"


def test_clean_plaintiff_keeps_different_companies_apart():
    assert clean_plaintiff("Discover Bank") != clean_plaintiff("Capital One, N.A.")
    assert clean_plaintiff("TD Bank USA, N.A.") != clean_plaintiff("TD Bank, N.A.")
    assert clean_plaintiff("") == ""


def test_lookup_names_a_known_plaintiff_and_leaves_unknown_ones_unclassified():
    names = load_names()
    assert display("CROWN ASSET MANAAGEMENT", names) == ("Crown Asset Management", "debt buyer")  # misspelling in the records
    assert display("SOME NEW FILER", names) == ("Some New Filer", "other or not classified")
    assert all(kind in {"debt buyer", "bank or card issuer", "consumer lender", "auto lender"} for _, kind in names.values())


def write_snapshot(root: Path, date: str, rows: list[dict]) -> None:
    d = root / date
    d.mkdir(parents=True)
    with (d / "debt_claims_filed.csv").open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=KEEP + ["Defendant Has Attorney"], restval="")
        w.writeheader()
        w.writerows(rows)


def test_build_counts_each_case_once_at_its_latest_status(tmp_path):
    base = {"Case File Date": "03/04/2025", "Plaintiff Name": "Lvnv Funding Llc", "Claim Amount": "1500.00",
            "Defendant Addr Zip": "77002", "Defendant Has Attorney": "N"}
    write_snapshot(tmp_path, "2026-01-01", [
        {**base, "Case Number": "A"},                                  # open in the first download
        {**base, "Case Number": "B", "Plaintiff Name": "LVNV FUNDING, LLC"},
    ])
    write_snapshot(tmp_path, "2026-02-01", [
        # Case A again, later: decided, and two rows because it has two parties.
        {**base, "Case Number": "A", "Disposition Desc": "Default Judgment (OCA)"},
        {**base, "Case Number": "A", "Disposition Desc": "Default Judgment (OCA)", "Defendant Has Attorney": "Y"},
    ])
    con = duckdb.connect()
    build(con, str(tmp_path), load_names())
    got = con.sql("SELECT case_number, plaintiff, kind, outcome, defendant_attorney, claim, zip, filed::VARCHAR "
                  "FROM cases ORDER BY 1").fetchall()
    assert got == [
        ("A", "LVNV Funding", "debt buyer", "default judgment", True, 1500.0, "77002", "2025-03-04"),
        ("B", "LVNV Funding", "debt buyer", "open", False, 1500.0, "77002", "2025-03-04"),
    ]


def test_cases_table_has_no_column_that_could_hold_a_defendant_name(tmp_path):
    write_snapshot(tmp_path, "2026-01-01", [{"Case Number": "A", "Case File Date": "01/02/2025", "Defendant Has Attorney": "N"}])
    con = duckdb.connect()
    build(con, str(tmp_path), load_names())
    cols = {c[0] for c in con.sql("DESCRIBE cases").fetchall()}
    assert cols == {"case_number", "snapshot", "filed", "court", "plaintiff", "kind", "plaintiff_attorney", "claim",
                    "zip", "defendant_attorney", "outcome"}
