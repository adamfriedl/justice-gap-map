import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from phase0_lsc_areas import classify, parse_area_list, parse_competition  # noqa: E402


def test_classify():
    assert classify("Serves all counties") == "all_counties"
    assert classify("Macomb, Oakland, Wayne") == "whole_counties"
    # County names containing compass words are still whole counties.
    assert classify("Armstrong, Westmoreland, Northampton") == "whole_counties"
    assert classify("Kern (northwest portion), Madera") == "partial"
    assert classify("Apache (the Navajo and Hopi reservation areas)") == "partial"


def test_parse_area_list():
    js = 'x=1,Kt=[{area:"AK-1",type:"Basic Field General",states:["02"],sortOrder:10},' \
         '{area:"MSX-2",type:"Agricultural Worker",states:["48","22"]}],y=2'
    assert parse_area_list(js) == [
        {"area": "AK-1", "type": "Basic Field General", "states": "02"},
        {"area": "MSX-2", "type": "Agricultural Worker", "states": "48 22"},
    ]


def test_parse_competition():
    page = """<table><tr><th>Service Area</th><th>State</th><th>Service Area Type</th><th>Poverty Population</th>
    <th>Estimated Grant ($)</th><th>Geographic Area</th><th>Learn More</th></tr>
    <tr><td>MI-13</td><td>MI</td><td>Basic Field - General</td><td>612,345</td><td>$6,983,000</td>
    <td>Macomb, Oakland, Wayne</td><td><a href="#">Map &amp; service info</a></td></tr>
    <tr><td>NCT-1</td><td>CT</td><td>Naative American</td><td>N/A</td><td>$22,699</td>
    <td> Serves all counties</td><td></td></tr></table>"""
    rows = parse_competition(page)
    assert rows[0] == {"area": "MI-13", "state": "MI", "type": "Basic Field - General",
                       "poverty_population": "612345", "estimated_grant": "6983000",
                       "geographic_area": "Macomb, Oakland, Wayne", "geography_class": "whole_counties"}
    assert rows[1]["type"] == "Native American" and rows[1]["poverty_population"] == ""
    assert rows[1]["geography_class"] == "all_counties"


from phase0_lsc_about import parse_area  # noqa: E402

COUNTIES = {"Georgia": ["Clayton County", "Cobb County", "Fulton County", "Bibb County"],
            "Puerto Rico": ["Adjuntas Municipio", "San Juan Municipio"]}


def test_parse_area_patterns():
    assert parse_area("Serves the following counties in Tennessee:\nFayette, Lauderdale", [], {}) == [
        ("Tennessee", "Fayette", False), ("Tennessee", "Lauderdale", False)]
    assert parse_area("Serves the following parishes in Louisiana:\nAcadia Parish, Allen Parish", [], {}) == [
        ("Louisiana", "Acadia Parish", False), ("Louisiana", "Allen Parish", False)]
    # "King and Queen" is one county; a list's final ", and" is not.
    assert [n for _, n, _ in parse_area("Arlington, King and Queen, and Loudoun", ["Virginia"], {})] == [
        "Arlington", "King and Queen", "Loudoun"]
    assert parse_area("Serves the following counties in California:\nKern (northwest portion), Madera", [], {}) == [
        ("California", "Kern", True), ("California", "Madera", False)]
    assert parse_area("Serves all counties in Georgia except Clayton, Cobb, and Fulton", [], COUNTIES) == [
        ("Georgia", "Bibb County", False)]
    assert parse_area("Serves Philadelphia", ["Pennsylvania"], {}) == [("Pennsylvania", "Philadelphia", False)]
    assert parse_area("Serves all of Puerto Rico except the Hato Rey area of San Juan Municipio", [], COUNTIES) == [
        ("Puerto Rico", "Adjuntas Municipio", False), ("Puerto Rico", "San Juan Municipio", True)]
