import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from lawsuits_fetch_harris import KEEP, safe_row  # noqa: E402


def test_safe_row_drops_defendant_identifiers():
    raw = {
        "Case Number ": "123", "Style Of Case ": "LVNV FUNDING LLC VS JANE DOE", "Plaintiff Name": "Lvnv Funding Llc",
        "Defendant Name": "JANE DOE", "Defendant Addr Line 1 ": "1 MAIN ST", "Defendant Addr Line 2 ": "APT 2",
        "Defendant Addr City ": "HOUSTON", "Defendant Addr Zip": "77002-1234", "Defendant Atty Name ": "",
        "Second Defendant Name": "JOHN DOE", "Judgment Against ": "JANE DOE", "Claim Amount": "3751.39",
    }
    out = safe_row(raw)
    flat = " ".join(out.values())
    for secret in ["JANE", "JOHN", "MAIN ST", "APT 2"]:
        assert secret not in flat
    assert set(out) == set(KEEP) | {"Defendant Has Attorney"}
    assert out["Defendant Addr Zip"] == "77002"
    assert out["Defendant Has Attorney"] == "N"
    assert out["Plaintiff Name"] == "Lvnv Funding Llc" and out["Case Number"] == "123"


def test_no_defendant_name_fields_kept():
    for k in KEEP:
        assert not (k.startswith(("Defendant", "Second Defendant")) and k != "Defendant Addr Zip")
    assert "Style Of Case" not in KEEP and "Judgment Against" not in KEEP
