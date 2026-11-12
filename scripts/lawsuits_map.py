"""Build a one-file HTML map of where debt lawsuits are filed.

One zoomed view per state with court data (Texas, Indiana, Virginia), plus a
national view of debt in collections for context. Texas also shows legal aid
offices and LSC service-area lines.

Reads the CSVs from scripts/lawsuits.py and scripts/tx_legal_aid.py, the Urban
debt-in-collections file, and the us-atlas county outlines (npm package
us-atlas@3.0.1, counties-10m.json, unprojected; the page projects each view).
Writes one HTML page with everything embedded.

    uv run python scripts/lawsuits_map.py \
        --atlas data/atlas/package/counties-10m.json --out site/index.html

site/index.html is what GitHub Pages serves (.github/workflows/pages.yml).
"""

import argparse
import csv
import json
from pathlib import Path

URBAN = "data/urban/2025-11-20/county_overall.csv"


def num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--lawsuits", default="docs/lawsuits")
    p.add_argument("--atlas", required=True)
    p.add_argument("--out", default="site/index.html")
    p.add_argument("--tx-year", type=int, default=2025)
    p.add_argument("--in-year", type=int, default=2024)
    p.add_argument("--legal-aid", default="docs/legal-aid/texas")
    a = p.parse_args()
    law = Path(a.lawsuits)

    data: dict[str, dict] = {}
    for r in csv.DictReader(open(URBAN)):
        data.setdefault(r["id"], {})["c"] = num(r["totcoll"]) and round(100 * num(r["totcoll"]), 1)
    for r in csv.DictReader(open(law / "county_filings_tx_in.csv")):
        want = a.tx_year if r["state"] == "TX" else a.in_year
        if int(r["year"]) != want:
            continue
        rep = num(r["reporting_pct"])
        d = data.setdefault(r["fips"], {})
        d.update(st=r["state"], y=want, n=num(r["filed"]), f=num(r["filed_per_1k"]),
                 dr=num(r["pct_default"]), rep=rep, pop=int(r["pop"]))
        if rep is not None and rep < 90:
            d["f"] = None  # incomplete court reporting: show as no data
            d["dr"] = None
            d["note"] = f"Courts filed {rep:.0f}% of expected reports; not mapped"
    for r in csv.DictReader(open(law / "virginia_courts_2025.csv")):
        for fips in r["fips"].split():
            d = data.setdefault(fips, {})
            d.update(st="VA", y=2025, n=num(r["general_civil"]), f=num(r["general_civil_per_1k"]),
                     g=num(r["garnishment_per_1k"]), court=r["court"], pop=int(r["pop"]))
    trend = [r for r in csv.DictReader(open(law / "state_trend.csv"))]

    # Texas legal aid layer: office points, service area and nearest-office distance per county.
    la = Path(a.legal_aid)
    offices = [{"o": r["office"], "lat": float(r["lat"]), "lon": float(r["lon"])}
               for r in csv.DictReader(open(la / "offices.csv"))]
    for r in csv.DictReader(open(la / "county_access.csv")):
        d = data.setdefault(r["fips"], {})
        d.update(sa=r["lsc_service_area"], no=r["nearest_office"], mi=num(r["nearest_office_miles"]),
                 oc=int(r["offices_in_county"]))
    for r in csv.DictReader(open(la / "directory_county.csv")):
        data.setdefault(r["fips"], {})["co"] = int(r["consumer_orgs_non_lsc_non_tax"])
    areas = [{k: r[k] for k in ("lsc_service_area", "offices", "lsc_eligible_population", "debt_suits_2025",
                                "suits_per_1k_eligible", "suits_per_office")}
             for r in csv.DictReader(open(la / "service_areas.csv"))]

    atlas = json.loads(Path(a.atlas).read_text())
    page = TEMPLATE.replace("/*ATLAS*/", json.dumps(atlas, separators=(",", ":"))) \
                   .replace("/*DATA*/", json.dumps(data, separators=(",", ":"))) \
                   .replace("/*TREND*/", json.dumps(trend, separators=(",", ":"))) \
                   .replace("/*OFFICES*/", json.dumps(offices, separators=(",", ":"))) \
                   .replace("/*AREAS*/", json.dumps(areas, separators=(",", ":"))) \
                   .replace("{{TX_YEAR}}", str(a.tx_year)).replace("{{IN_YEAR}}", str(a.in_year))
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB)")


TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Where Debt Lawsuits Are Filed</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  /* Layout: header, layer switch, map with legend, then trend and county tables side by side. */
  --bg: #f6f7f8; --surface: #ffffff; --ink: #1d2329; --muted: #5d6873; --line: #dde2e7;
  --accent: #8a2c1f; --nodata: #e6e9ec;
  --s1: #fbe9e3; --s2: #f3bfae; --s3: #e08b72; --s4: #c0553c; --s5: #8a2c1f;
  --display: "Source Serif 4", Georgia, serif; --body: "IBM Plex Sans", system-ui, sans-serif;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #15191d; --surface: #1d2328; --ink: #e8ecef; --muted: #9aa5ae; --line: #2f373e;
  --accent: #f08c6e; --nodata: #2a3137;
  --s1: #3a2622; --s2: #6b3428; --s3: #a3472f; --s4: #d96a4b; --s5: #f7a183; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #15191d; --surface: #1d2328; --ink: #e8ecef; --muted: #9aa5ae; --line: #2f373e;
  --accent: #f08c6e; --nodata: #2a3137;
  --s1: #3a2622; --s2: #6b3428; --s3: #a3472f; --s4: #d96a4b; --s5: #f7a183; color-scheme: dark; }
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 var(--body); }
main { max-width: 1120px; margin: 0 auto; padding: 24px 16px 48px; display: grid; gap: 20px; }
h1 { font: 600 30px/1.15 var(--display); margin: 0; text-wrap: balance; }
h2 { font: 600 19px/1.25 var(--display); margin: 0 0 8px; text-wrap: balance; }
.lede { color: var(--muted); max-width: 68ch; margin: 6px 0 0; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px; }
.switch { display: flex; flex-wrap: wrap; gap: 8px; }
.switch button { font: 500 14px var(--body); padding: 7px 12px; border-radius: 6px; border: 1px solid var(--line);
  background: var(--surface); color: var(--ink); cursor: pointer; }
.switch button[aria-pressed="true"] { background: var(--accent); border-color: var(--accent); color: var(--surface); }
.switch button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
#map { width: 100%; height: auto; max-height: 720px; display: block; }
#map path.county { stroke: var(--surface); stroke-width: 0.25; }
#map path.state { fill: none; stroke: var(--muted); stroke-width: 0.6; pointer-events: none; }
#map path.outline { fill: none; stroke: var(--ink); stroke-width: 1; pointer-events: none; }
#map path.sa { fill: none; stroke: var(--ink); stroke-width: 2; stroke-dasharray: 5 3; pointer-events: none; }
#map circle.office { fill: var(--surface); stroke: var(--ink); stroke-width: 1.6; }
#map circle.office:hover { fill: var(--ink); }
.views { display: flex; flex-wrap: wrap; gap: 6px; border-bottom: 1px solid var(--line); padding-bottom: 12px; margin-bottom: 12px; }
.views button { font: 600 15px var(--body); padding: 8px 14px; border-radius: 6px; border: 1px solid transparent;
  background: transparent; color: var(--muted); cursor: pointer; }
.views button[aria-pressed="true"] { color: var(--ink); border-color: var(--line); background: var(--bg); }
.views button:focus-visible { outline: 2px solid var(--accent); outline-offset: 2px; }
.toggle { font-size: 14px; display: inline-flex; align-items: center; gap: 6px; margin-left: 6px; }
.facts { display: flex; flex-wrap: wrap; gap: 24px; margin: 4px 0 10px; }
.facts div { font-size: 13px; color: var(--muted); }
.facts b { display: block; font: 600 22px var(--display); color: var(--ink); }
.hidden { display: none !important; }
.grid2.one { grid-template-columns: 1fr; }
#map text.sa-label { font: 600 13px var(--body); fill: var(--ink); paint-order: stroke; stroke: var(--surface); stroke-width: 4px; pointer-events: none; }
#map path.county:hover { stroke: var(--ink); stroke-width: 1; }
.legend { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; font-size: 13px; color: var(--muted); margin-top: 8px; }
.legend .sw { display: inline-flex; align-items: center; gap: 4px; }
.legend i { width: 18px; height: 12px; border-radius: 2px; display: inline-block; }
.layer-note { font-size: 13px; color: var(--muted); margin: 6px 0 0; max-width: 90ch; }
#tip { position: fixed; pointer-events: none; background: var(--surface); border: 1px solid var(--line); border-radius: 6px;
  padding: 8px 10px; font-size: 13px; box-shadow: 0 4px 14px rgba(0,0,0,.15); display: none; max-width: 280px; z-index: 5; }
#tip b { display: block; font-weight: 600; }
#tip .muted { color: var(--muted); }
.grid2 { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
@media (max-width: 760px) { .grid2 { grid-template-columns: 1fr; } }
table { width: 100%; border-collapse: collapse; font-size: 13.5px; font-variant-numeric: tabular-nums; }
th, td { text-align: left; padding: 5px 6px; border-bottom: 1px solid var(--line); }
th { color: var(--muted); font-weight: 500; }
td.n, th.n { text-align: right; }
.tabs { display: flex; gap: 6px; margin-bottom: 8px; }
.tabs button { font: 500 13px var(--body); padding: 4px 10px; border-radius: 5px; border: 1px solid var(--line);
  background: transparent; color: var(--ink); cursor: pointer; }
.tabs button[aria-pressed="true"] { border-color: var(--accent); color: var(--accent); }
.notes { font-size: 13.5px; color: var(--muted); max-width: 80ch; }
.notes li { margin: 4px 0; }
.notes a { color: var(--accent); }
@media (prefers-reduced-motion: reduce) { * { transition: none !important; } }
</style>
</head>
<body>
<main>
  <header>
    <h1>Where debt lawsuits are filed</h1>
    <p class="lede">Debt-collection lawsuits by county, in the states whose courts publish them in a usable form. There's no national count of debt suits, so each state is shown on its own, against its own counties. A national view of debt in collections is there for context. <a href="docket/">Who files in Harris County, and how the cases end</a></p>
  </header>
  <section class="panel">
    <div class="views" role="group" aria-label="View">
      <button data-v="TX" aria-pressed="true">Texas</button>
      <button data-v="IN" aria-pressed="false">Indiana</button>
      <button data-v="VA" aria-pressed="false">Virginia</button>
      <button data-v="US" aria-pressed="false">National: debt in collections</button>
    </div>
    <div class="facts" id="facts"></div>
    <div class="switch" role="group" aria-label="Map layer" id="switch"></div>
    <svg id="map" role="img" aria-label="County map"></svg>
    <div class="legend" id="legend"></div>
    <p class="layer-note" id="layer-note"></p>
  </section>
  <section class="grid2" id="side">
    <div class="panel" id="trend-panel">
      <h2>Filings over time</h2>
      <svg id="trend" viewBox="0 0 520 260" role="img" aria-label="Debt lawsuit filings by year"></svg>
      <p class="layer-note" id="trend-note"></p>
    </div>
    <div class="panel">
      <h2 id="top-title">Highest filing rates</h2>
      <table><thead><tr><th>County</th><th class="n">Filed</th><th class="n">Per 1K</th><th class="n" id="th3">Default %</th></tr></thead>
      <tbody id="top"></tbody></table>
      <p class="layer-note">Counties with 50,000+ residents.</p>
    </div>
  </section>
  <section class="panel" id="areas-panel">
    <h2>Texas legal aid service areas</h2>
    <table><thead><tr><th>LSC service area</th><th class="n">Offices</th><th class="n">Eligible residents</th><th class="n">2025 debt suits</th><th class="n">Suits per 1K eligible</th><th class="n">Suits per office</th></tr></thead>
    <tbody id="areas"></tbody></table>
    <p class="layer-note">Each area is served by one LSC-funded program. "Eligible" is LSC's count of residents under 125% of poverty. "Offices" are locations listed on the programs' websites (2026-11-08). These describe how many suits arrive in an area relative to the legal aid footprint there, not how any program performs; debt defense is one of many kinds of cases legal aid takes on. <a href="https://github.com/adamfriedl/justice-gap-map/blob/main/docs/legal-aid/texas.md">Method and caveats</a>.</p>
  </section>
  <section class="panel notes">
    <h2>What the numbers are</h2>
    <ul>
      <li><b>Texas:</b> new "Debt Claim" cases in justice courts, from the Office of Court Administration's Court Activity database (calendar year). Debt claims are suits by debt buyers, collectors and lenders; larger suits in county and district courts are not included. Counties whose courts sent fewer than 90% of their monthly reports are left blank (Hidalgo sent none).</li>
      <li><b>Indiana:</b> new "Collection" (CC) cases in all courts in the county, from Indiana Court Online Reports. Small-claims cases, which include some debt suits, are not counted here.</li>
      <li><b>Virginia:</b> "General Civil" filings in General District Court, 2025, from the court system's filing report. Most are warrants in debt, but the category also holds other civil cases; its county pattern tracks true warrant-in-debt counts from 2016–2019 closely (rank correlation 0.75). Some courts serve more than one locality, so those localities share a rate.</li>
      <li><b>Default share:</b> default judgments as a share of all cases disposed that year.</li>
      <li><b>LSC-funded legal aid offices (Texas):</b> locations listed on the websites of the three LSC-funded Texas programs, 2026-11-08, placed at their city. Distance is a straight line from the county's center to the nearest office. Phone and online intake, outreach sites, and programs without LSC funding are not shown.</li>
      <li><b>Consumer-law help beyond LSC (Texas):</b> organizations the Texas Access to Justice Commission's directory lists for each county with a "Consumer/Transactional" tag, not counting the area's LSC-funded program or low-income taxpayer clinics, 2026-11-09. It shows coverage, not offices or capacity.</li>
      <li><b>Debt in collections:</b> Urban Institute, Debt in America: share of people with a credit record who have any debt in collections, August 2025.</li>
      <li>Rates use ACS 2020–2024 population. Built from public data; the scripts, sources, and caveats are in the <a href="https://github.com/adamfriedl/justice-gap-map">project repository</a> (<a href="https://github.com/adamfriedl/justice-gap-map/blob/main/docs/lawsuits/README.md">methods and findings</a>).</li>
    </ul>
  </section>
</main>
<div id="tip" role="tooltip"></div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.9.0/d3.min.js"></script>
<script src="https://cdnjs.cloudflare.com/ajax/libs/topojson/3.0.2/topojson.min.js"></script>
<script>
const atlas = /*ATLAS*/;
const data = /*DATA*/;
const trend = /*TREND*/;
const offices = /*OFFICES*/;
const areas = /*AREAS*/;
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const ramp = () => ["--s1","--s2","--s3","--s4","--s5"].map(css);
const fmtInt = d3.format(",");
const all = topojson.feature(atlas, atlas.objects.counties).features;
const ST = {"01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE","11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV","55":"WI","56":"WY","72":"PR"};
const VIEWS = {
  TX: { fips: "48", name: "Texas", year: {{TX_YEAR}}, layers: ["f", "dr", "mi", "co"] },
  IN: { fips: "18", name: "Indiana", year: {{IN_YEAR}}, layers: ["f", "dr"] },
  VA: { fips: "51", name: "Virginia", year: 2025, layers: ["f"] },
  US: { name: "United States", layers: ["c"] },
};
const LAYERS = {
  f: { button: "Lawsuits per 1,000 residents", label: "lawsuits per 1,000 residents, in fifths of the state's counties", fmt: v => v.toFixed(1), get: d => d.f,
       note: "Hover a county for its numbers. Grey: courts filed fewer than 90% of their expected reports." },
  dr: { button: "Default judgments", label: "% of disposed debt cases ending in default, in fifths of the state's counties", fmt: v => v.toFixed(0) + "%", get: d => d.dr,
        note: "Default judgments as a share of debt cases disposed that year." },
  mi: { button: "Miles to an LSC-funded office", label: "straight-line miles from the county's center to the nearest LSC-funded legal aid office", fmt: v => v.toFixed(0), get: d => d.mi, cuts: [0.5, 25, 50, 75],
        legendText: ["office in county", "under 25", "25–49", "50–74", "75+"],
        note: "Distance from each county's center to the nearest office listed by the three LSC-funded Texas programs. 81% of 2025 debt suits were filed in counties with one. Other legal aid nonprofits, clinics, and hotlines are not shown yet." },
  co: { button: "Consumer-law help beyond LSC", label: "organizations listing consumer-law help for the county, besides the LSC-funded program and tax clinics", fmt: v => v.toFixed(0), get: d => d.co, cuts: [1, 2, 3], reverse: true,
        legendText: ["none", "1", "2", "3 or more"],
        note: "From the Texas Access to Justice Commission's county directory (2026-11-09). Every county lists its LSC-funded program; this counts the others. A listing shows coverage, not office locations or capacity. In South Texas most single listings are one organization that works with community groups, which may overstate help for individuals." },
  c: { button: "Debt in collections", label: "% of people with a credit record who have debt in collections", fmt: v => v.toFixed(0) + "%", get: d => d.c,
       note: "Urban Institute, August 2025. Available for every county, so it gives national context; it counts people being collected on, not lawsuits." },
};
let view = "TX", layer = "f", showOffices = true;
const svg = d3.select("#map"), tip = d3.select("#tip");

function feats() { return view === "US" ? all : all.filter(f => String(f.id).slice(0, 2) === VIEWS[view].fips); }
function projection(fc, W) {
  if (view === "US") return d3.geoAlbersUsa().fitWidth(W, fc);
  const lon = d3.geoCentroid(fc)[0];
  return d3.geoConicEqualArea().parallels([29.5, 45.5]).rotate([-lon, 0]).fitWidth(W, fc);
}
function draw() {
  const V = VIEWS[view], L = LAYERS[layer], R = ramp(), W = 960;
  const fs = feats(), fc = { type: "FeatureCollection", features: fs };
  const proj = projection(fc, W), path = d3.geoPath(proj);
  const [[, y0], [, y1]] = path.bounds(fc), H = Math.ceil(y1 - y0 + 8);
  svg.attr("viewBox", `0 ${Math.floor(y0) - 4} ${W} ${H}`).selectAll("*").remove();
  const vals = fs.map(f => data[f.id] && L.get(data[f.id])).filter(v => v != null && isFinite(v));
  // "reverse": fewer is darker (used where the layer counts help available, so darker still means less).
  const RR = L.reverse ? [R[4], R[3], R[2], R[1]] : R;
  const scale = L.cuts ? d3.scaleThreshold().domain(L.cuts).range(RR) : d3.scaleQuantile().domain(vals).range(R);
  svg.append("g").selectAll("path").data(fs).join("path").attr("class", "county").attr("d", path)
    .attr("fill", f => { const d = data[f.id]; const v = d && L.get(d); return v == null || !isFinite(v) ? css("--nodata") : scale(v); })
    .on("mousemove", (ev, f) => showTip(ev, countyTip(f))).on("mouseleave", hideTip);
  if (view === "US") {
    svg.append("path").attr("class", "state").attr("d", path(topojson.mesh(atlas, atlas.objects.states, (a, b) => a !== b)));
  } else {
    const st = atlas.objects.states.geometries.filter(g => g.id === V.fips);
    svg.append("path").attr("class", "outline").attr("d", path(topojson.merge(atlas, st)));
  }
  if (view === "TX") {
    const geoms = atlas.objects.counties.geometries;
    const sa = id => data[id] && data[id].sa;
    svg.append("path").attr("class", "sa").attr("d", path(topojson.mesh(atlas, { type: "GeometryCollection", geometries: geoms },
      (a, b) => a !== b && String(a.id).startsWith("48") && String(b.id).startsWith("48") && sa(a.id) && sa(b.id) && sa(a.id) !== sa(b.id))));
    for (const a of areas) {
      const g = atlas.objects.counties.geometries.filter(c => data[c.id] && data[c.id].sa === a.lsc_service_area);
      const [x, y] = path.centroid(topojson.merge(atlas, g));
      svg.append("text").attr("class", "sa-label").attr("x", x).attr("y", y).attr("text-anchor", "middle").text(a.lsc_service_area);
    }
    if (showOffices) svg.append("g").selectAll("circle").data(offices).join("circle").attr("class", "office").attr("r", 4.5)
      .attr("transform", o => `translate(${proj([o.lon, o.lat])})`)
      .on("mousemove", (ev, o) => showTip(ev, `<b>LSC-funded legal aid office</b><div>${o.o}</div>`)).on("mouseleave", hideTip);
  }
  // legend
  let html = `<span>${L.label}:</span>`;
  if (L.cuts) html += RR.map((c, i) => `<span class="sw"><i style="background:${c}"></i>${L.legendText[i]}</span>`).join("");
  else if (view === "US") { const t = scale.quantiles(), cuts = [d3.min(vals), ...t];
    html += R.map((c, i) => `<span class="sw"><i style="background:${c}"></i>${L.fmt(cuts[i])}${i < 4 ? "–" + L.fmt(cuts[i + 1]) : "+"}</span>`).join(""); }
  else { html += R.map((c, i) => `<span class="sw"><i style="background:${c}"></i>${["lowest","","middle","","highest"][i]}</span>`).join("");
    const t = scale.quantiles(), ext = d3.extent(vals);
    html += `<span class="sw">range ${L.fmt(ext[0])}–${L.fmt(ext[1])}; fifths at ${t.map(L.fmt).join(" / ")}</span>`; }
  html += `<span class="sw"><i style="background:${css("--nodata")}"></i>no data</span>`;
  if (view === "TX") html += `<span class="sw"><svg width="14" height="14"><circle cx="7" cy="7" r="4.5" fill="${css("--surface")}" stroke="${css("--ink")}" stroke-width="1.6"/></svg>LSC-funded legal aid office</span>
    <span class="sw"><svg width="22" height="8"><line x1="0" y1="4" x2="22" y2="4" stroke="${css("--ink")}" stroke-width="2" stroke-dasharray="5 3"/></svg>LSC service area</span>`;
  d3.select("#legend").html(html);
  d3.select("#layer-note").text(L.note);
}
function countyTip(f) {
  const d = data[f.id] || {}, nm = f.properties.name, st = d.st || ST[String(f.id).slice(0, 2)];
  let h = `<b>${nm}${st ? ", " + st : ""}</b>`;
  if (view === "US") return h + (d.c != null ? `<div>${d.c.toFixed(0)}% of people with a credit record have debt in collections</div>` : `<div class="muted">No value (fewer than 50 people in the sample)</div>`);
  if (d.court && d.court !== nm) h += `<div>Court: ${d.court}</div>`;
  if (d.f != null) h += `<div>${fmtInt(d.n)} filed in ${d.y} · ${d.f.toFixed(1)} per 1K</div>`;
  if (d.note) h += `<div>${d.note}</div>`;
  if (d.dr != null) h += `<div>${d.dr.toFixed(0)}% of disposed cases were defaults</div>`;
  if (d.g != null) h += `<div>Garnishments: ${d.g.toFixed(1)} per 1K</div>`;
  if (d.sa) h += `<div>${d.oc ? (d.oc > 1 ? d.oc + " LSC-funded legal aid offices" : "LSC-funded legal aid office") + " in county" : "Nearest LSC-funded legal aid office: " + d.no + ", " + d.mi.toFixed(0) + " mi"} · ${d.sa}</div>`;
  if (d.co != null && view === "TX") h += `<div>Consumer-law help listed beyond LSC: ${d.co ? d.co + " organization" + (d.co > 1 ? "s" : "") : "none"}</div>`;
  if (d.c != null) h += `<div class="muted">Context: ${d.c.toFixed(0)}% with debt in collections</div>`;
  return h;
}
function showTip(ev, h) { tip.html(h).style("display", "block").style("left", Math.min(ev.clientX + 14, innerWidth - 290) + "px").style("top", (ev.clientY + 14) + "px"); }
function hideTip() { tip.style("display", "none"); }
function facts() {
  const V = VIEWS[view];
  if (view === "US") { d3.select("#facts").html(""); return; }
  const rows = Object.values(data).filter(d => d.st === view && d.n != null);
  const courts = new Set(), n = d3.sum(rows, d => { if (d.court) { if (courts.has(d.court)) return 0; courts.add(d.court); } return d.n; });
  const tr = trend.filter(t => t.state === view), last = tr[tr.length - 1];
  let h = `<div><b>${fmtInt(Math.round(last && +last.year === V.year ? +last.filed : n))}</b>${view === "VA" ? "General Civil filings (mostly debt suits)" : "debt suits filed"}, ${V.year}</div>`;
  if (last && last.pct_default) h += `<div><b>${(+last.pct_default).toFixed(0)}%</b>of disposed cases ended in default</div>`;
  if (tr.length > 1) { const first = tr.find(t => +t.rows > (view === "IN" ? 80 : 0)) || tr[0];
    h += `<div><b>${(+last.filed / +first.filed).toFixed(1)}×</b>the ${first.year} count</div>`; }
  if (view === "TX") h += `<div><b>${offices.length}</b>LSC-funded legal aid offices</div>`;
  d3.select("#facts").html(h);
}
function switches() {
  const V = VIEWS[view];
  if (!V.layers.includes(layer)) layer = V.layers[0];
  let h = V.layers.map(k => `<button data-l="${k}" aria-pressed="${k === layer}">${LAYERS[k].button}</button>`).join("");
  if (view === "TX") h += `<label class="toggle"><input type="checkbox" id="off" ${showOffices ? "checked" : ""}> show LSC-funded offices</label>`;
  d3.select("#switch").html(h).classed("hidden", V.layers.length < 2 && view !== "TX");
  document.querySelectorAll("#switch button").forEach(b => b.addEventListener("click", () => { layer = b.dataset.l; switches(); draw(); }));
  const off = document.getElementById("off"); if (off) off.addEventListener("change", e => { showOffices = e.target.checked; draw(); });
}
function trendChart() {
  const s = d3.select("#trend"); s.selectAll("*").remove();
  const pts = trend.filter(d => d.state === view && +d.rows > (view === "IN" ? 80 : 0)).map(d => [+d.year, +d.filed]);
  d3.select("#trend-note").text(view === "TX" ? "Justice-court debt claims, statewide. The case type began in September 2013." :
    view === "IN" ? "Collection cases, all courts, statewide." : "Virginia's filing report is used for 2025 only so far.");
  if (pts.length < 2) { s.append("text").attr("x", 20).attr("y", 40).attr("fill", css("--muted")).text("One year of data so far."); return; }
  const W = 520, H = 260, m = {l: 54, r: 70, t: 12, b: 28};
  const x = d3.scaleLinear().domain(d3.extent(pts, d => d[0])).range([m.l, W - m.r]);
  const y = d3.scaleLinear().domain([0, d3.max(pts, d => d[1])]).nice().range([H - m.b, m.t]);
  s.append("g").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(6).tickFormat(d3.format("d")))
    .call(a => { a.selectAll("line,path").attr("stroke", css("--line")); a.selectAll("text").attr("fill", css("--muted")); });
  s.append("g").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(".2s")).tickSize(-(W - m.l - m.r)))
    .call(a => { a.select(".domain").remove(); a.selectAll("line").attr("stroke", css("--line")); a.selectAll("text").attr("fill", css("--muted")); });
  s.append("path").attr("fill", "none").attr("stroke", css("--s5")).attr("stroke-width", 2.2).attr("d", d3.line().x(d => x(d[0])).y(d => y(d[1]))(pts));
  const last = pts[pts.length - 1];
  s.append("circle").attr("cx", x(last[0])).attr("cy", y(last[1])).attr("r", 3.5).attr("fill", css("--s5"));
  s.append("text").attr("x", x(last[0]) + 6).attr("y", y(last[1]) + 4).attr("fill", css("--ink")).attr("font-size", 12).text(fmtInt(last[1]));
}
function showTop() {
  const seen = new Set(), rows = [];
  for (const f of feats()) {
    const d = data[f.id];
    if (!d || d.st !== view || d.f == null || d.pop < 50000) continue;
    const key = d.court || f.id; if (seen.has(key)) continue; seen.add(key);
    rows.push({nm: d.court && view === "VA" ? d.court : f.properties.name, ...d});
  }
  rows.sort((a, b) => b.f - a.f);
  document.getElementById("top-title").textContent = `Highest filing rates in ${VIEWS[view].name}`;
  document.getElementById("th3").textContent = view === "VA" ? "Garnish. /1K" : "Default %";
  document.getElementById("top").innerHTML = rows.slice(0, 12).map(r =>
    `<tr><td>${r.nm}</td><td class="n">${fmtInt(r.n)}</td><td class="n">${r.f.toFixed(1)}</td><td class="n">${
      view === "VA" ? (r.g != null ? r.g.toFixed(1) : "–") : (r.dr != null ? r.dr.toFixed(0) : "–")}</td></tr>`).join("");
}
document.getElementById("areas").innerHTML = areas.map(a => `<tr><td>${a.lsc_service_area}</td><td class="n">${a.offices}</td><td class="n">${fmtInt(+a.lsc_eligible_population)}</td><td class="n">${fmtInt(Math.round(+a.debt_suits_2025))}</td><td class="n">${(+a.suits_per_1k_eligible).toFixed(1)}</td><td class="n">${fmtInt(Math.round(+a.suits_per_office))}</td></tr>`).join("");
function render() {
  document.querySelectorAll(".views button").forEach(b => b.setAttribute("aria-pressed", b.dataset.v === view));
  d3.select("#side").classed("hidden", view === "US").classed("one", view === "VA");
  d3.select("#trend-panel").classed("hidden", view === "VA");
  d3.select("#areas-panel").classed("hidden", view !== "TX");
  switches(); draw(); facts();
  if (view !== "US") { trendChart(); showTop(); }
  history.replaceState(null, "", "#" + view.toLowerCase());
}
document.querySelectorAll(".views button").forEach(b => b.addEventListener("click", () => { view = b.dataset.v; render(); }));
const h0 = location.hash.slice(1).toUpperCase(); if (VIEWS[h0]) view = h0;
render();
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", render);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
