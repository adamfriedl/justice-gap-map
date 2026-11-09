"""Texas prototype: where are legal aid offices, and how far is each county from one?

Reads office pages saved from the three LSC-funded Texas programs' websites
(fetched 2026-11-08 into data/txlegalaid/2026-11-08/), places each office at its
city's Census internal point (2024 Gazetteer), finds the county it sits in, and
measures each county's distance to the nearest office. Joins Texas debt-suit
filing rates (docs/lawsuits/county_filings_tx_in.csv).

    uv run python scripts/tx_legal_aid.py --out docs/legal-aid/texas

Place-based by design (PRD "Purely informational"): it describes where offices
are, not how any program performs.
"""

import argparse
import csv
import html
import math
import re
from pathlib import Path

import duckdb

RAW = Path("data/txlegalaid/2026-11-08")
GAZ = Path("data/census/gazetteer/2024")
ATLAS = Path("data/atlas/package/counties-10m.json")  # us-atlas@3.0.1, unprojected
FILINGS = Path("docs/lawsuits/county_filings_tx_in.csv")
AREAS = Path("docs/phase0/lsc-data/area_county.csv")

SOURCES = {
    "Lone Star Legal Aid": "https://www.lonestarlegal.org/offices/",
    "Legal Aid of NorthWest Texas": "https://legalaidtx.org/locations/",
    "Texas RioGrande Legal Aid": "https://www.trla.org/offices",
}


def lines(path: Path) -> list[str]:
    t = path.read_text(errors="replace")
    t = re.sub(r"(?s)<(script|style)[^>]*>.*?</\1>", "", t)
    t = re.sub(r"<br\s*/?>", "\n", t)
    t = html.unescape(re.sub(r"<[^>]+>", "\n", t))
    return [x.strip().rstrip(",").strip() for x in t.split("\n") if x.strip()]


def tx_counties() -> dict[str, str]:
    """County name (without ' County') -> FIPS, from the 2024 Gazetteer."""
    out = {}
    with open(GAZ / "2024_Gaz_counties_national.txt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            r = {k.strip(): v.strip() for k, v in r.items()}
            if r["USPS"] == "TX":
                out[r["NAME"].removesuffix(" County")] = r["GEOID"]
    return out


def served_after(ls: list[str], i: int, names: set[str]) -> list[str]:
    """County names listed right after a 'Counties Served' heading."""
    out = []
    for x in ls[i + 1:]:
        if x in names:
            out.append(x)
        elif out:
            break
    return out


def parse_offices(names: set[str]) -> list[dict]:
    offices = []
    # Lone Star Legal Aid: the offices page lists each office with the counties it serves.
    ls = lines(RAW / "lsla_offices.html")
    for i, x in enumerate(ls):
        m = re.fullmatch(r"(.+) Office", x)
        if m and i + 1 < len(ls) and ls[i + 1].startswith("Counties Served"):
            city = m.group(1)
            page = RAW / f"lsla_{city.lower().replace(' ', '-')}-office.html"
            addr = ""
            if page.exists():
                pl = lines(page)
                z = [j for j, y in enumerate(pl) if re.search(r"(TX|Texas)\.?,?\s+\d{5}", y) and "1415 Fannin" not in pl[j - 1]]
                addr = z and pl[z[0]] or ""
            if city == "Houston":
                addr = "Houston, TX 77002"
            offices.append(dict(program="Lone Star Legal Aid", office=city, city=city,
                                address_line=addr, served=served_after(ls, i + 1, names),
                                note="" if addr else "no street address on the office page"))
    # Legal Aid of NorthWest Texas: one page per office, each with "Counties Served".
    for page in sorted(RAW.glob("lanwt_*.html")):
        if page.name == "lanwt_locations.html":
            continue
        pl = lines(page)
        city = {"fort-worth": "Fort Worth", "san-angelo": "San Angelo", "wichita-falls": "Wichita Falls",
                "mckinney": "McKinney"}.get(page.stem[6:], page.stem[6:].replace("-", " ").title())
        i = next(j for j, y in enumerate(pl) if y.startswith("Counties Served"))
        offices.append(dict(program="Legal Aid of NorthWest Texas", office=city, city=city, address_line="",
                            served=served_after(pl, i, names), note=""))
    # Texas RioGrande Legal Aid: addresses only.
    pl = lines(RAW / "trla_offices.html")
    seen, admin_only = set(), set()
    for j, y in enumerate(pl):
        m = re.search(r"^(.+?),\s*(?:TX|Texas)\.?\s+(\d{5})", y)
        if not m:
            continue
        city = m.group(1).strip()
        context = " ".join(pl[max(0, j - 4):j])
        if "administration staff only" in context:
            admin_only.add(city)  # Mercedes: administration only, no attorneys or intake on site
        if city in admin_only or (city, y) in seen:
            continue
        seen.add((city, y))
        label = "Corpus Christi (courthouse)" if "Courthouse" in context else city
        offices.append(dict(program="Texas RioGrande Legal Aid", office=label, city=city, address_line=y,
                            served=[], note="help desk in the county courthouse" if "Courthouse" in context else ""))
    return offices


def place_points() -> dict[str, tuple[float, float]]:
    pts = {}
    with open(GAZ / "2024_Gaz_place_national.txt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            r = {k.strip(): v.strip() for k, v in r.items()}
            if r["USPS"] != "TX":
                continue
            nm = re.sub(r" (city|town|village|CDP)$", "", r["NAME"])
            pts.setdefault(nm, (float(r["INTPTLAT"]), float(r["INTPTLONG"])))
    return pts


def county_points() -> dict[str, tuple[float, float, str]]:
    out = {}
    with open(GAZ / "2024_Gaz_counties_national.txt") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            r = {k.strip(): v.strip() for k, v in r.items()}
            if r["USPS"] == "TX":
                out[r["GEOID"]] = (float(r["INTPTLAT"]), float(r["INTPTLONG"]), r["NAME"].removesuffix(" County"))
    return out


def county_polygons() -> dict[str, list[list[tuple[float, float]]]]:
    """Decode Texas county rings (lon, lat) from the us-atlas TopoJSON."""
    import json
    topo = json.loads(ATLAS.read_text())
    (sx, sy), (tx, ty) = topo["transform"]["scale"], topo["transform"]["translate"]
    arcs = []
    for arc in topo["arcs"]:
        x = y = 0
        pts = []
        for dx, dy in arc:
            x += dx
            y += dy
            pts.append((x * sx + tx, y * sy + ty))
        arcs.append(pts)

    def ring(idx):
        out = []
        for a in idx:
            pts = arcs[a] if a >= 0 else arcs[~a][::-1]
            out.extend(pts if not out else pts[1:])
        return out

    polys = {}
    for g in topo["objects"]["counties"]["geometries"]:
        if not str(g.get("id", "")).startswith("48"):
            continue
        parts = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
        polys[g["id"]] = [ring(r) for p in parts for r in p]
    return polys


def inside(pt, rings) -> bool:
    lon, lat = pt
    hit = False
    for r in rings:  # even-odd rule across all rings handles holes
        for (x1, y1), (x2, y2) in zip(r, r[1:] + r[:1]):
            if (y1 > lat) != (y2 > lat) and lon < (x2 - x1) * (lat - y1) / (y2 - y1) + x1:
                hit = not hit
    return hit


def miles(a, b) -> float:
    la1, lo1, la2, lo2 = map(math.radians, (a[0], a[1], b[0], b[1]))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 3958.8 * 2 * math.asin(math.sqrt(h))


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--out", default="docs/legal-aid/texas")
    a = p.parse_args()
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    names = tx_counties()
    offices = parse_offices(set(names))
    places, cpts, polys = place_points(), county_points(), county_polygons()
    for o in offices:
        lat, lon = places[o["city"]]
        o["lat"], o["lon"] = lat, lon
        hits = [f for f, rings in polys.items() if inside((lon, lat), rings)]
        # A city point can fall in water at this map resolution (Corpus Christi lands in the bay):
        # use the county whose internal point is nearest instead.
        o["county_fips"] = hits[0] if hits else min(cpts, key=lambda f: miles((lat, lon), cpts[f][:2]))
        o["county"] = cpts[o["county_fips"]][2]
    with open(out / "offices.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["program", "office", "city", "address_line", "county_fips", "county", "lat", "lon",
                    "counties_served", "note", "source", "fetched"])
        for o in offices:
            w.writerow([o["program"], o["office"], o["city"], o["address_line"], o["county_fips"], o["county"],
                        round(o["lat"], 5), round(o["lon"], 5), "; ".join(o["served"]), o["note"],
                        SOURCES[o["program"]], "2026-11-08"])

    area = {r["county_fips"]: r["area"] for r in csv.DictReader(open(AREAS)) if r["state"] == "Texas"}
    with open(out / "county_access.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["fips", "county", "lsc_service_area", "offices_in_county", "nearest_office", "nearest_office_miles"])
        for fips, (lat, lon, nm) in sorted(cpts.items()):
            near = min(offices, key=lambda o: miles((lat, lon), (o["lat"], o["lon"])))
            w.writerow([fips, nm, area.get(fips, ""), sum(o["county_fips"] == fips for o in offices),
                        near["office"], round(miles((lat, lon), (near["lat"], near["lon"])), 1)])

    c = duckdb.connect()
    c.sql(f"""create view j as
      select a.*, f.filed, f.filed_per_1k, f.pct_default, f.reporting_pct, f.pop, f.pct_lt125
      from read_csv_auto('{out / "county_access.csv"}', types={{'fips': 'VARCHAR'}}) a
      join read_csv_auto('{FILINGS}', types={{'fips': 'VARCHAR'}}) f
        on f.fips = a.fips and f.state = 'TX' and f.year = 2025""")
    c.sql(f"""copy (
      select case when offices_in_county > 0 then '0: office in county'
                  when nearest_office_miles < 50 then '1: under 50 miles'
                  when nearest_office_miles < 100 then '2: 50-99 miles'
                  else '3: 100+ miles' end as distance_band,
             count(*) as counties, sum(pop) as population,
             round(sum(pop * pct_lt125 / 100)) as pop_under_125pct_poverty,
             sum(filed) filter (where reporting_pct >= 90) as debt_suits_2025_full_reporting,
             round(median(filed_per_1k) filter (where reporting_pct >= 90), 1) as median_suits_per_1k
      from j group by 1 order by 1) to '{out / "distance_bands.csv"}' (header)""")
    c.sql(f"""copy (
      select a.lsc_service_area, count(*) as counties, sum(a.offices_in_county) as offices,
             s.eligible as lsc_eligible_population, s.award_amount as lsc_award_fy2025,
             sum(j.filed) as debt_suits_2025,
             sum(j.filed) filter (where j.reporting_pct >= 90) as debt_suits_2025_full_reporting,
             round(1000.0 * sum(j.filed) / s.eligible, 1) as suits_per_1k_eligible,
             round(sum(j.filed) / sum(a.offices_in_county)) as suits_per_office,
             round(sum(j.filed) / (s.award_amount / 1e6)) as suits_per_lsc_million
      from read_csv_auto('{out / "county_access.csv"}', types={{'fips': 'VARCHAR'}}) a
      left join j using (fips)
      join read_csv_auto('docs/phase0/lsc-data/service_areas_about.csv') s on s.area = a.lsc_service_area
      group by a.lsc_service_area, s.eligible, s.award_amount order by 1) to '{out / "service_areas.csv"}' (header)""")
    rho = c.sql("""select count(*), corr(r1, r2) from (
        select rank() over (order by filed_per_1k) r1, rank() over (order by nearest_office_miles) r2
        from j where reporting_pct >= 90)""").fetchall()[0]
    rho_pov = c.sql("""select corr(r1, r2) from (
        select rank() over (order by pct_lt125) r1, rank() over (order by nearest_office_miles) r2 from j)""").fetchall()[0][0]
    with open(out / "checks.csv", "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["check", "n", "spearman"])
        w.writerow(["TX 2025 debt suits per 1K vs miles to nearest office (counties with 90%+ reporting)", rho[0], round(rho[1], 3)])
        w.writerow(["TX share under 125% poverty vs miles to nearest office (all counties)", 254, round(rho_pov, 3)])
    print(f"{len(offices)} offices; wrote {out}")


if __name__ == "__main__":
    main()
