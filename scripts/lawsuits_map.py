"""Build a one-file HTML map of where debt lawsuits are filed.

Reads the CSVs from scripts/lawsuits.py, the Urban debt-in-collections file, and
the us-atlas county outlines (npm package us-atlas@3.0.1, counties-albers-10m.json,
pre-projected). Writes one HTML page with everything embedded.

    uv run python scripts/lawsuits_map.py \
        --atlas data/atlas/package/counties-albers-10m.json --out site/index.html

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

    atlas = json.loads(Path(a.atlas).read_text())
    page = TEMPLATE.replace("/*ATLAS*/", json.dumps(atlas, separators=(",", ":"))) \
                   .replace("/*DATA*/", json.dumps(data, separators=(",", ":"))) \
                   .replace("/*TREND*/", json.dumps(trend, separators=(",", ":"))) \
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
#map { width: 100%; height: auto; display: block; }
#map path.county { stroke: var(--surface); stroke-width: 0.25; }
#map path.state { fill: none; stroke: var(--muted); stroke-width: 0.6; pointer-events: none; }
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
    <p class="lede">Debt-collection lawsuits per 1,000 residents, by county, in the three states with open county court counts used here: Texas ({{TX_YEAR}}), Indiana ({{IN_YEAR}}) and Virginia (2025). Other states have no county court counts here and show in grey. The debt-in-collections view covers every county, for context.</p>
  </header>
  <section class="panel">
    <div class="switch" role="group" aria-label="Map layer">
      <button id="b-f" aria-pressed="true">Lawsuits per 1,000 residents</button>
      <button id="b-dr" aria-pressed="false">Default judgments (TX, IN)</button>
      <button id="b-c" aria-pressed="false">Debt in collections (all counties)</button>
    </div>
    <svg id="map" viewBox="0 0 975 610" role="img" aria-label="County map of the United States"></svg>
    <div class="legend" id="legend"></div>
    <p class="layer-note" id="layer-note"></p>
  </section>
  <section class="grid2">
    <div class="panel">
      <h2>Filings over time</h2>
      <svg id="trend" viewBox="0 0 520 260" role="img" aria-label="Debt lawsuit filings by year"></svg>
      <p class="layer-note">Texas: justice-court debt claims, statewide. Indiana: collection cases, all courts. The Texas case type began in September 2013.</p>
    </div>
    <div class="panel">
      <h2>Highest filing rates</h2>
      <div class="tabs" role="group" aria-label="State">
        <button data-st="TX" aria-pressed="true">Texas</button>
        <button data-st="IN" aria-pressed="false">Indiana</button>
        <button data-st="VA" aria-pressed="false">Virginia</button>
      </div>
      <table><thead><tr><th>County</th><th class="n">Filed</th><th class="n">Per 1K</th><th class="n" id="th3">Default %</th></tr></thead>
      <tbody id="top"></tbody></table>
      <p class="layer-note">Counties with 50,000+ residents.</p>
    </div>
  </section>
  <section class="panel notes">
    <h2>What the numbers are</h2>
    <ul>
      <li><b>Texas:</b> new "Debt Claim" cases in justice courts, from the Office of Court Administration's Court Activity database (calendar year). Debt claims are suits by debt buyers, collectors and lenders; larger suits in county and district courts are not included. Counties whose courts sent fewer than 90% of their monthly reports are left blank (Hidalgo sent none).</li>
      <li><b>Indiana:</b> new "Collection" (CC) cases in all courts in the county, from Indiana Court Online Reports. Small-claims cases, which include some debt suits, are not counted here.</li>
      <li><b>Virginia:</b> "General Civil" filings in General District Court, 2025, from the court system's filing report. Most are warrants in debt, but the category also holds other civil cases; its county pattern tracks true warrant-in-debt counts from 2016–2019 closely (rank correlation 0.75). Some courts serve more than one locality, so those localities share a rate.</li>
      <li><b>Default share:</b> default judgments as a share of all cases disposed that year.</li>
      <li><b>Debt in collections:</b> Urban Institute, Debt in America, credit-bureau data from August 2025.</li>
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
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const ramp = () => ["--s1","--s2","--s3","--s4","--s5"].map(css);
const counties = topojson.feature(atlas, atlas.objects.counties).features;
const states = topojson.mesh(atlas, atlas.objects.states, (a, b) => a !== b);
const svg = d3.select("#map"), path = d3.geoPath();
const g = svg.append("g");
const cp = g.selectAll("path.county").data(counties).join("path").attr("class", "county").attr("d", path);
g.append("path").attr("class", "state").attr("d", path(states));
const LAYERS = {
  f: { label: "lawsuits per 1,000 residents, in fifths within each state", perState: true, fmt: v => v.toFixed(1), get: d => d.f,
       note: "Each state is shaded against its own counties, because the three states count cases differently (Virginia's category is broader). Hover for the actual rate. Grey: no county court counts used for that state, or incomplete court reporting." },
  dr: { label: "% of disposed debt cases ending in default, in fifths within each state", perState: true, fmt: v => v.toFixed(0) + "%", get: d => d.dr,
        note: "Each state is shaded against its own counties. Virginia's filing report has no disposition breakdown, so it is blank on this layer." },
  c: { label: "% of people with debt in collections", fmt: v => v.toFixed(0) + "%", get: d => d.c,
       note: "Share of people with a credit record who have any debt in collections, August 2025." },
};
let layer = "f";
function draw() {
  const L = LAYERS[layer], R = ramp();
  const groups = {};
  for (const d of Object.values(data)) {
    const v = L.get(d); if (v == null || !isFinite(v)) continue;
    (groups[L.perState ? d.st : "all"] ||= []).push(v);
  }
  const scales = Object.fromEntries(Object.entries(groups).map(([k, v]) => [k, d3.scaleQuantile().domain(v).range(R)]));
  cp.attr("fill", f => { const d = data[f.id]; const v = d && L.get(d);
    return v == null ? css("--nodata") : scales[L.perState ? d.st : "all"](v); });
  let html = `<span>${L.label}:</span>`;
  if (L.perState) {
    html += R.map((c, i) => `<span class="sw"><i style="background:${c}"></i>${["lowest","","middle","","highest"][i] || ""}</span>`).join("");
    html += Object.entries(scales).map(([st, q]) => { const t = q.quantiles(), dom = d3.extent(q.domain());
      return `<span class="sw">${st}: ${L.fmt(dom[0])}–${L.fmt(dom[1])}, fifths at ${t.map(L.fmt).join(" / ")}</span>`; }).join("");
  } else {
    const q = scales.all, t = q.quantiles(), cuts = [d3.min(q.domain()), ...t];
    html += R.map((c, i) => `<span class="sw"><i style="background:${c}"></i>${L.fmt(cuts[i])}${i < 4 ? "–" + L.fmt(cuts[i+1]) : "+"}</span>`).join("");
  }
  d3.select("#legend").html(html + `<span class="sw"><i style="background:${css("--nodata")}"></i>no data</span>`);
  d3.select("#layer-note").text(L.note);
}
["f","dr","c"].forEach(k => document.getElementById("b-" + k).addEventListener("click", e => {
  layer = k; document.querySelectorAll(".switch button").forEach(b => b.setAttribute("aria-pressed", b === e.currentTarget));
  draw(); }));
const tip = d3.select("#tip");
// State postal codes by FIPS prefix, so every tooltip names the state.
const ST = {"01":"AL","02":"AK","04":"AZ","05":"AR","06":"CA","08":"CO","09":"CT","10":"DE","11":"DC","12":"FL","13":"GA","15":"HI","16":"ID","17":"IL","18":"IN","19":"IA","20":"KS","21":"KY","22":"LA","23":"ME","24":"MD","25":"MA","26":"MI","27":"MN","28":"MS","29":"MO","30":"MT","31":"NE","32":"NV","33":"NH","34":"NJ","35":"NM","36":"NY","37":"NC","38":"ND","39":"OH","40":"OK","41":"OR","42":"PA","44":"RI","45":"SC","46":"SD","47":"TN","48":"TX","49":"UT","50":"VT","51":"VA","53":"WA","54":"WV","55":"WI","56":"WY","72":"PR"};
cp.on("mousemove", (ev, f) => {
  const d = data[f.id] || {}, nm = f.properties.name, st = d.st || ST[String(f.id).slice(0, 2)];
  let h = `<b>${nm}${st ? ", " + st : ""}</b>`;
  if (d.court && d.court !== nm) h += `<div>Court: ${d.court}</div>`;
  if (d.f != null) h += `<div>${d.n.toLocaleString()} filed in ${d.y} · ${d.f.toFixed(1)} per 1K</div>`;
  else if (layer !== "c" && !d.note) h += `<div class="muted">No county court counts for this state</div>`;
  if (d.note) h += `<div>${d.note}</div>`;
  if (d.dr != null) h += `<div>${d.dr.toFixed(0)}% of disposed cases were defaults</div>`;
  if (d.g != null) h += `<div>Garnishments: ${d.g.toFixed(1)} per 1K</div>`;
  if (d.c != null) h += layer === "c"
    ? `<div>${d.c.toFixed(0)}% of people with a credit record have debt in collections</div>`
    : `<div class="muted">Context: ${d.c.toFixed(0)}% with debt in collections</div>`;
  tip.html(h).style("display", "block").style("left", Math.min(ev.clientX + 14, innerWidth - 290) + "px").style("top", (ev.clientY + 14) + "px");
}).on("mouseleave", () => tip.style("display", "none"));
// Trend chart
(function () {
  const W = 520, H = 260, m = {l: 54, r: 118, t: 12, b: 28};
  const s = d3.select("#trend"), years = d3.extent(trend, d => +d.year);
  const x = d3.scaleLinear().domain(years).range([m.l, W - m.r]);
  const y = d3.scaleLinear().domain([0, d3.max(trend, d => +d.filed)]).nice().range([H - m.b, m.t]);
  s.append("g").attr("transform", `translate(0,${H - m.b})`).call(d3.axisBottom(x).ticks(6).tickFormat(d3.format("d")))
    .call(a => { a.selectAll("line,path").attr("stroke", css("--line")); a.selectAll("text").attr("fill", css("--muted")); });
  s.append("g").attr("transform", `translate(${m.l},0)`).call(d3.axisLeft(y).ticks(5).tickFormat(d3.format(".2s")).tickSize(-(W - m.l - m.r)))
    .call(a => { a.select(".domain").remove(); a.selectAll("line").attr("stroke", css("--line")); a.selectAll("text").attr("fill", css("--muted")); });
  const cols = {TX: css("--s5"), IN: css("--s3")};
  for (const st of ["TX", "IN"]) {
    const pts = trend.filter(d => d.state === st && +d.rows > (st === "IN" ? 80 : 0)).map(d => [+d.year, +d.filed]);
    if (!pts.length) continue;
    s.append("path").attr("fill", "none").attr("stroke", cols[st]).attr("stroke-width", 2.2)
      .attr("d", d3.line().x(d => x(d[0])).y(d => y(d[1]))(pts));
    const last = pts[pts.length - 1];
    s.append("circle").attr("cx", x(last[0])).attr("cy", y(last[1])).attr("r", 3.5).attr("fill", cols[st]);
    s.append("text").attr("x", x(last[0]) + 6).attr("y", y(last[1]) + 4).attr("fill", css("--ink"))
      .attr("font-size", 12).text(`${st === "TX" ? "Texas" : "Indiana"} ${d3.format(",")(last[1])}`);
  }
})();
// Top counties table
function showTop(st) {
  document.querySelectorAll(".tabs button").forEach(b => b.setAttribute("aria-pressed", b.dataset.st === st));
  const seen = new Set(), rows = [];
  for (const f of counties) {
    const d = data[f.id];
    if (!d || d.st !== st || d.f == null || d.pop < 50000) continue;
    const key = d.court || f.id; if (seen.has(key)) continue; seen.add(key);
    rows.push({nm: d.court && st === "VA" ? d.court : f.properties.name, ...d});
  }
  rows.sort((a, b) => b.f - a.f);
  document.getElementById("th3").textContent = st === "VA" ? "Garnish. /1K" : "Default %";
  document.getElementById("top").innerHTML = rows.slice(0, 12).map(r =>
    `<tr><td>${r.nm}</td><td class="n">${d3.format(",")(r.n)}</td><td class="n">${r.f.toFixed(1)}</td><td class="n">${
      st === "VA" ? (r.g != null ? r.g.toFixed(1) : "–") : (r.dr != null ? r.dr.toFixed(0) : "–")}</td></tr>`).join("");
}
document.querySelectorAll(".tabs button").forEach(b => b.addEventListener("click", () => showTop(b.dataset.st)));
draw(); showTop("TX");
window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", draw);
</script>
</body>
</html>
"""

if __name__ == "__main__":
    main()
