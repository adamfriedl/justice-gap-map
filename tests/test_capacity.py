import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from phase0_capacity import NORM_NAME, parse_grantees, parse_profile  # noqa: E402

PAGE = """
<div class="accordion accordion--collapsed paragraph">
  <div class="field field--name-field-plain-title field__item">Alabama</div>
  <div class="accordion__content"><div><p>(<a href="/node/1402">State Totals</a>)</p>
  <ul><li><a href="/node/961">Legal Services Alabama</a></li></ul></div></div>
</div>
<div class="accordion accordion--collapsed paragraph">
  <div class="field field--name-field-plain-title field__item">Texas</div>
  <div class="accordion__content"><div><ul><li><a href="/node/1">Lone Star Legal Aid</a></li>
  <li><a href="/node/2">Texas RioGrande Legal Aid, Inc.</a></li></ul></div></div>
</div>
"""

PROFILE = """CIVIL LEGAL NEEDS & SERVICES IN
LSC GRANTEES
Legal Services Alabama, Inc.
Alabama
1 in 5 people
$8,415,245
to serve the eligible population
LSC ELIGIBLE JUSTICE GAP STUDY HOUSING ISSUES
SERVED IN CASES (2025) TOP CLOSED CASES FUNDING IN 2026"""


def test_parse_grantees():
    assert parse_grantees(PAGE) == [
        ("Alabama", "Legal Services Alabama"),
        ("Texas", "Lone Star Legal Aid"),
        ("Texas", "Texas RioGrande Legal Aid, Inc."),
    ]


def test_parse_profile():
    assert parse_profile(PROFILE) == {"lsc_funding": 8415245, "lsc_funding_year": 2026, "state_name": "Alabama"}
    assert parse_profile("no amount here") == {}


def test_norm_name():
    con = duckdb.connect()
    con.sql(NORM_NAME)
    f = lambda s: con.sql("SELECT norm_name(?)", params=[s]).fetchall()[0][0]  # noqa: E731
    assert f("Legal Services Alabama, Inc.") == f("LEGAL SERVICES ALABAMA INC") == "LEGAL SERVICES ALABAMA"
    assert f("Legal Aid of the Bluegrass") == "LEGAL AID BLUEGRASS"
    assert f("Bay Area Legal Aid & Co") == "BAY AREA LEGAL AID AND"
