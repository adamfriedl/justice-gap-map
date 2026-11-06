import sys
from pathlib import Path

import duckdb

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from phase0_cfpb_zip import ZIP_CLASS_SQL  # noqa: E402


def classify(z):
    return duckdb.sql(f"SELECT {ZIP_CLASS_SQL} FROM (SELECT ?::VARCHAR AS zip)", params=[z]).fetchall()[0][0]


def test_zip_classes():
    assert classify("75202") == "zip5"
    assert classify("00501") == "zip5"
    assert classify("296XX") == "zip3"
    for z in ["XXXXX", None, "", "2011-", "202-3", "7520", "752021", "29XXX"]:
        assert classify(z) == "none", z
