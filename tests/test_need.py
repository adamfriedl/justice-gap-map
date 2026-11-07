import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from phase0_need import NORM_COUNTY, parse_tx_rows, spearman, spearman_within_state  # noqa: E402

# Shaped like an OCA "Justice Court Activity Detail" Excel export: labels and
# values sit at fixed column positions, with empty cells in between.
SHEET = [
    ["", "Justice Courts Activity Detail\nJanuary 1, 2025 to December 31, 2025\n"],
    ["", "91.7 Percent Reporting Rate"],
    ["", "44 Reports Received Out of a Possible 48  "],
    ["", "County: De Witt"],
    ["", "CRIMINAL CASES"],
    ["", "", "New Cases Filed", "999", "", "", "", "999"],  # criminal table: must be ignored
    ["", "CIVIL CASES"],
    ["", "", "", "", "", "", "", "\n\nDebt Claim", "", "", "", "", "\n\nLandlord/Tenant", "", "", "\n\nSmall Claims"],
    ["", "", "\xa0\xa0\xa0\xa0Active Cases", "", "", "", "", "579", "", "", "", "", "87"],
    ["", "", "New Cases Filed", "", "", "", "", "1,657", "", "", "", "", "184"],
    ["", "", "Default Judgments", "", "", "", "", "---", "", "", "", "", "54"],
    ["", "", "Total Cases Disposed", "", "", "", "", "481", "", "", "", "", "12"],
    ["", "", "New Cases Filed", "", "", "", "", "5", "", "", "", "", "5"],  # later table: ignored
]


def test_parse_tx_rows():
    r = parse_tx_rows(SHEET)
    assert r == {
        "reporting_pct": 91.7, "reports_received": 44, "reports_possible": 48,
        "county_name": "De Witt", "debt_filed": 1657.0, "debt_default": 0.0, "debt_disposed": 481.0,
    }


def test_norm_county_matches_acs_spelling():
    con = duckdb.connect()
    con.sql(NORM_COUNTY)
    assert con.sql("SELECT norm_county('De Witt') = norm_county('DeWitt')").fetchall()[0][0]
    assert con.sql("SELECT norm_county('La Salle') = norm_county('LaSalle')").fetchall()[0][0]


def test_spearman():
    con = duckdb.connect()
    con.sql("""CREATE TABLE t AS SELECT * FROM (VALUES
        ('01', 1, 10), ('01', 2, 20), ('01', 3, 30), ('02', 10, 3), ('02', 20, 2), ('02', 30, 1))
        AS v(state_fips, x, y)""")
    assert con.sql(spearman("t", "x", "y")).fetchall()[0] == (6, -0.771)  # ranks 1..6 vs 4,5,6,3,2,1
    # Within each state the order is perfect, one way in each: they cancel to zero.
    assert con.sql(spearman_within_state("t", "x", "y")).fetchall()[0] == (6, 0.0)


def test_indiana_cells():
    sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
    from lawsuits import in_cells

    grid = {"Tables": [{
        "ColumnSections": [{"Columns": [{"Title3": "rowLabels"}, {"Title3": "CC"}, {"Title3": "SC"}]}],
        "RowSections": [{"Rows": [
            {"isTitle": True, "Title": "BEFORE COURT", "Cells": []},
            {"Title": "New Filings", "Cells": [{"TxtVal": "New Filings"}, {"TxtVal": "4,729"}, {"TxtVal": "11645"}]},
            {"Title": "Default", "Cells": [{"TxtVal": "Default"}, {"TxtVal": ""}, {"TxtVal": "5201"}]},
        ]}],
    }]}
    assert in_cells(grid, "New Filings", "CC") == 4729
    assert in_cells(grid, "New Filings", "SC") == 11645
    assert in_cells(grid, "Default", "CC") is None
    assert in_cells(grid, "New Filings", "MF") is None
