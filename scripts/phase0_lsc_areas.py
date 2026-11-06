"""Phase 0: what LSC service-area data can be downloaded, and can service areas be
rebuilt from counties?

Reads two public lsc.gov sources and writes CSVs to --out:

- the full service-area list embedded in lsc.gov's service-area map module
  (code, type, states);
- the "2027 Service Areas Subject to Competition" table, which gives each listed
  area's counties, poverty population, and estimated grant. Only areas up for
  competition that year are listed (awards run up to three years).

    uv run python scripts/phase0_lsc_areas.py --raw data/lsc/2026-11-06 --out docs/phase0/lsc-data

Raw pages are saved under --raw (gitignored).
"""

import argparse
import csv
import html
import re
import urllib.request
from pathlib import Path

UA = {"User-Agent": "justice-gap-map research (Python urllib)"}
MAP_JS = "https://www.lsc.gov/modules/custom/lsc_serv_areas_map/lsc_serv_areas_map_app/dist/assets/index.js?v=1.x"
COMPETITION = "https://www.lsc.gov/grants/basic-field-grant/lsc-service-areas/2027-service-areas-subject-competition"

# Words in a geographic description that mean part of a county, not all of it.
PARTIAL_RE = re.compile(r"\bportions?\b|\bpart of\b|reservation|\bexcept\b|\bexcluding\b", re.I)


def get(url: str, save: Path) -> str:
    if not save.exists():
        with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=120) as r:
            save.write_bytes(r.read())
    return save.read_text(errors="ignore")


def parse_area_list(js: str) -> list[dict]:
    start = js.index("Kt=[")
    block = js[start:js.index("}]", start) + 2]
    return [{"area": a, "type": t, "states": " ".join(re.findall(r'"(\d+)"', s))}
            for a, t, s in re.findall(r'\{area:"([^"]+)",type:"([^"]+)",states:\[([^\]]*)\]', block)]


def cell_text(s: str) -> str:
    return html.unescape(re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", s))).strip()


def parse_competition(page: str) -> list[dict]:
    rows = []
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", page, re.S):
        cells = [cell_text(c) for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", tr, re.S)]
        if len(cells) < 6 or cells[0] == "Service Area":
            continue
        area, state, typ, pov, grant, geo = cells[:6]
        typ = typ.replace("Naative", "Native")  # typo on the LSC page
        rows.append({"area": area, "state": state, "type": typ,
                     "poverty_population": pov.replace(",", "") if pov != "N/A" else "",
                     "estimated_grant": re.sub(r"[$,]", "", grant), "geographic_area": geo,
                     "geography_class": classify(geo)})
    return rows


def classify(geo: str) -> str:
    """'all_counties', 'whole_counties' (a list of county names), or 'partial'."""
    if re.fullmatch(r"Serves all counties\.?", geo.strip(), re.I):
        return "all_counties"
    if PARTIAL_RE.search(geo) or "(" in geo:
        return "partial"
    return "whole_counties"


def write(rows: list[dict], path: Path) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {path} ({len(rows)} rows)")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--raw", default="data/lsc/2026-11-06")
    p.add_argument("--out", default="docs/phase0/lsc-data")
    a = p.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    raw.mkdir(parents=True, exist_ok=True)
    out.mkdir(parents=True, exist_ok=True)

    areas = parse_area_list(get(MAP_JS, raw / "serv_areas_map_index.js"))
    write(areas, out / "service_areas.csv")
    comp = parse_competition(get(COMPETITION, raw / "2027-service-areas-subject-competition.html"))
    write(comp, out / "competition_2027.csv")

    summary = {}
    for r in comp:
        key = (r["type"], r["geography_class"])
        summary[key] = summary.get(key, 0) + 1
    types = {}
    for r in areas:
        types[r["type"]] = types.get(r["type"], 0) + 1
    rows = [{"source": "map module", "type": t, "geography_class": "", "areas": n} for t, n in sorted(types.items())]
    rows += [{"source": "2027 competition", "type": t, "geography_class": g, "areas": n}
             for (t, g), n in sorted(summary.items())]
    write(rows, out / "summary.csv")


if __name__ == "__main__":
    main()
