"""Phase 0: rebuild LSC Basic Field-General service areas from counties.

Downloads LSC's public description of every service area (the JSON behind the
lsc.gov service-area map), parses each area's county list, matches the names to
Census county FIPS codes, and checks that every county is covered.

    uv run python scripts/phase0_lsc_about.py \
        --areas docs/phase0/lsc-data/service_areas.csv \
        --acs data/acs/county_acs5_2024.json \
        --raw data/lsc/2026-11-07/about --out docs/phase0/lsc-data

Raw JSON lands under --raw (gitignored). The `delineation` codes come from LSC:
3 means a county is split along minor civil divisions (towns, cities), 4 along
census tracts (per the map's own notes). The meanings of 1, 2, and 7 are inferred
from the descriptions (statewide, whole counties, Puerto Rico) and not confirmed.
"""

import argparse
import csv
import json
import re
import time
import urllib.request
from pathlib import Path

API = "https://api.lscdataease.org/public/lsc/service_areas/{}/about.json"
UA = {"User-Agent": "justice-gap-map research (Python urllib)"}
SPLIT_CODES = {3, 4, 7}
SUFFIXES = (" County", " Parish", " Borough", " Census Area", " City and Borough", " Municipality",
            " Municipio", " city")


def fetch(areas: list[str], raw: Path, pause: float) -> None:
    raw.mkdir(parents=True, exist_ok=True)
    for area in areas:
        path = raw / f"{area}.json"
        if path.exists():
            continue
        with urllib.request.urlopen(urllib.request.Request(API.format(area), headers=UA), timeout=60) as r:
            path.write_bytes(r.read())
        time.sleep(pause)


def norm(name: str) -> str:
    name = name.replace("St.", "Saint").replace("Ste.", "Sainte")
    return re.sub(r"[^a-z]", "", name.lower())


def acs_counties(path: Path) -> dict[tuple[str, str], str]:
    """(state name, normalized county name) -> county FIPS. Names are indexed with
    and without their suffix; independent cities keep 'city' to stay distinct
    from a same-named county (e.g. Richmond city vs. Richmond County, VA)."""
    rows = json.loads(path.read_text())[1:]
    out = {}
    for r in rows:
        county, state = [s.strip() for s in r[0].rsplit(",", 1)]
        fips = r[-2] + r[-1]
        out[(state, norm(county))] = fips
        if not county.endswith(" city"):
            for suf in SUFFIXES:
                if county.endswith(suf):
                    out.setdefault((state, norm(county[: -len(suf)])), fips)
    return out


# County renamed since LSC wrote its descriptions.
RENAMED = {("South Dakota", "shannon"): "oglalalakota"}


def split_names(names: str) -> list[tuple[str, bool]]:
    """'Adams, Kern (northwest portion), and Lee' -> [(name, partial?), ...]."""
    out = []
    # Split on commas outside parentheses; a list's final ", and" goes too, but
    # "King and Queen" (one county) stays whole.
    for item in re.split(r",(?![^()]*\))\s*(?:and\s+)?", names):
        item = re.sub(r"^and\s+", "", item.strip().rstrip("."))
        if item:
            out.append((re.sub(r"\s*\(.*?\)\s*", "", item).strip(), "(" in item))
    return out


def parse_area(desc: str, states: list[str], counties_in: dict[str, list[str]]) -> list[tuple[str, str, bool]]:
    """(state, county name, partial?) for every county a general area covers.

    Handles LSC's description patterns: a header line ("Serves the following
    counties|parishes|counties and independent cities in X:") then a list;
    "Serves all counties in X [except A, B, and C]"; "Serves all of X"; a bare
    list; or a single place ("Serves Philadelphia").
    """
    desc = desc.strip()
    if m := re.match(r"Serves all of Puerto Rico except the Hato Rey area of San Juan", desc):
        return [("Puerto Rico", c, c == "San Juan Municipio") for c in counties_in["Puerto Rico"]]
    if re.match(r"Serves the Hato Rey area of San Juan", desc):
        return [("Puerto Rico", "San Juan", True)]
    if m := re.match(r"Serves all (?:counties|islands)(?: or county equivalents)? in ([^\n]+?)(?: except (.+))?$", desc):
        state, excluded = m.group(1).strip(), {norm(n) for n, _ in split_names(m.group(2) or "")}
        return [(state, c, False) for c in counties_in.get(state, []) if norm(c) not in excluded
                and not any(norm(c).startswith(e) and norm(c)[len(e):] in ("county", "parish", "") for e in excluded)]
    if m := re.match(r"Serves all of (.+)$", desc):
        state = m.group(1).strip()
        return [(state, c, False) for c in counties_in.get(state, [])]
    blocks = re.findall(r"Serves the following [^:\n]* in ([^:\n]+):\s*\n([^\n]+)", desc)
    if blocks:
        return [(st.strip(), n, part) for st, names in blocks for n, part in split_names(names)]
    state = states[0] if states else ""
    if m := re.match(r"Serves ([^,\n]+)$", desc):
        return [(state, n, part) for n, part in split_names(m.group(1))]
    return [(state, n, part) for n, part in split_names(desc)]


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--areas", default="docs/phase0/lsc-data/service_areas.csv")
    p.add_argument("--acs", default="data/acs/county_acs5_2024.json")
    p.add_argument("--raw", default="data/lsc/2026-11-07/about")
    p.add_argument("--out", default="docs/phase0/lsc-data")
    p.add_argument("--pause", type=float, default=0.5)
    a = p.parse_args()
    raw, out = Path(a.raw), Path(a.out)
    areas = [r["area"] for r in csv.DictReader(open(a.areas))]
    fetch(areas, raw, a.pause)
    county_fips = acs_counties(Path(a.acs))
    counties_in: dict[str, list[str]] = {}
    for r in json.loads(Path(a.acs).read_text())[1:]:
        county, state = [x.strip() for x in r[0].rsplit(",", 1)]
        counties_in.setdefault(state, []).append(county)
    state_of = {fips[:2]: state for (state, _), fips in county_fips.items()}

    summary, links, unmatched = [], [], []
    for area in areas:
        d = json.loads((raw / f"{area}.json").read_text())
        desc = d["area"]["area_description"]
        codes = set(d["area"].get("delineation") or [])
        award = d.get("latest_awards") or {}
        grantee = (d.get("current_grantee") or {}).get("name", "")
        general = "General" in d["service_area_type"]
        statewide = bool(re.match(r"Serves all (counties|islands)[^\n]*$", desc)) and "except" not in desc
        parsed = parse_area(desc, d["area"].get("state_name") or [], counties_in) if general else []
        for state, name, partial in parsed:
            key = (state, norm(name))
            fips = county_fips.get((state, RENAMED.get(key, key[1])))
            if fips is None:
                unmatched.append({"area": area, "state": state, "name": name})
            else:
                links.append({"area": area, "county_fips": fips, "state": state, "county": name, "partial": partial})
        summary.append({
            "area": area, "type": d["service_area_type"], "grantee": grantee,
            "award_fy": award.get("fy", ""), "award_amount": award.get("amount", ""),
            "funding_pop": award.get("funding_pop", ""), "eligible": (d.get("demographics") or {}).get("eligible", ""),
            "delineation": " ".join(str(c) for c in sorted(codes)),
            "structure": ("statewide" if statewide else "splits_counties" if codes & SPLIT_CODES or
                          any(x[2] for x in parsed) else "whole_counties"),
            "counties": len(parsed),
            "next_year_in_comp": (d.get("competition") or {}).get("next_year_in_comp", ""),
            "description": desc.replace("\n", " | "),
        })

    # Dedupe statewide links (county_fips dict holds several name keys per county).
    seen, deduped = set(), []
    for link in links:
        key = (link["area"], link["county_fips"])
        if key not in seen:
            seen.add(key)
            deduped.append(link)
    links = deduped

    # Coverage: how many general areas claim each county.
    claims: dict[str, list[dict]] = {}
    for link in links:
        claims.setdefault(link["county_fips"], []).append(link)
    all_fips = {f for f in county_fips.values()}
    coverage = []
    for fips in sorted(all_fips):
        c = claims.get(fips, [])
        coverage.append({"county_fips": fips, "state": state_of.get(fips[:2], ""),
                         "areas": " ".join(sorted(x["area"] for x in c)), "n_areas": len(c),
                         "any_partial": any(x["partial"] for x in c)})

    # Analysis units: general areas that share a split county are merged, so
    # every county belongs to exactly one unit. Union-find over shared counties.
    parent = {r["area"]: r["area"] for r in summary if "General" in r["type"]}

    def find(x):
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for c in claims.values():
        for other in c[1:]:
            parent[find(other["area"])] = find(c[0]["area"])
    groups: dict[str, list[str]] = {}
    for area in parent:
        groups.setdefault(find(area), []).append(area)
    units = [{"area": area, "unit": "+".join(sorted(groups[find(area)])), "unit_size": len(groups[find(area)])}
             for area in sorted(parent)]

    for rows, name in [(summary, "service_areas_about.csv"), (units, "analysis_units.csv"), (links, "area_county.csv"),
                       (coverage, "county_coverage.csv"), (unmatched or [{"area": "", "state": "", "name": ""}],
                                                           "unmatched_county_names.csv")]:
        with (out / name).open("w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(rows[0]))
            w.writeheader()
            w.writerows(rows)
        print(f"wrote {out / name} ({len(rows)} rows)")


if __name__ == "__main__":
    main()
