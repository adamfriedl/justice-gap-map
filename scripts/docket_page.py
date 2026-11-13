"""Build the docket page (site/index.html, the published front page) from the tables in docs/docket/.

    uv run python scripts/docket.py          # the tables, from data/harris/
    uv run python scripts/docket_page.py     # the page, from the tables

The page has no dependencies: charts are inline SVG written here, and a few
lines of script show a tooltip. Every figure on it comes from a committed CSV.
"""

import argparse
import csv
import html
from pathlib import Path

KINDS = [  # column in by_month.csv, label, color slot
    ("debt_buyer", "Debt buyers", "c1"),
    ("bank_or_card_issuer", "Banks and card issuers", "c2"),
    ("lender", "Consumer and auto lenders", "c3"),
    ("other_or_not_classified", "Other or not classified", "c4"),
]
OUTCOMES = [  # column, label, color slot, label ink on that fill
    ("pct_default_judgment", "Default judgment", "c1", "#fff"),
    ("pct_dropped_by_plaintiff", "Dropped by the plaintiff", "c2", "#fff"),
    ("pct_agreed_judgment", "Agreed judgment", "c3", "#111"),
    ("pct_dismissed_not_pursued", "Dismissed, plaintiff did not pursue", "c4", "#111"),
    ("pct_trial_or_other", "Trial or other", "c5", "#111"),
    ("pct_open", "Still open", "open", "inherit"),
]


def read(path: Path) -> list[dict]:
    with path.open() as f:
        return list(csv.DictReader(f))


def n(x) -> str:
    return f"{int(float(x)):,}"


def esc(s) -> str:
    return html.escape(str(s), quote=True)


def month_label(m: str) -> str:
    y, mo = m.split("-")
    return ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"][int(mo) - 1] + " " + y


def chart_months(rows: list[dict]) -> str:
    """Stacked bars: cases filed each month, by kind of plaintiff."""
    W, H, L, R, T, B = 880, 300, 46, 8, 10, 30
    top = max(int(r["cases"]) for r in rows)
    ymax = (top // 2500 + 1) * 2500
    step = (W - L - R) / len(rows)
    bw = step - 6
    y = lambda v: T + (H - T - B) * (1 - v / ymax)  # noqa: E731
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="Debt claims filed each month in Harris County justice courts, by kind of plaintiff">']
    for tick in range(0, ymax + 1, 2500):
        out.append(f'<line class="grid" x1="{L}" x2="{W - R}" y1="{y(tick):.1f}" y2="{y(tick):.1f}"/>'
                   f'<text class="axis" x="{L - 8}" y="{y(tick) + 4:.1f}" text-anchor="end">{tick:,}</text>')
    for i, r in enumerate(rows):
        x, base = L + i * step + 3, 0
        tip = f"{month_label(r['month'])}: {n(r['cases'])} cases. " + ", ".join(
            f"{label} {n(r[col])}" for col, label, _ in KINDS)
        out.append(f'<g class="bar" data-tip="{esc(tip)}"><rect class="hit" x="{x - 3:.1f}" y="{T}" width="{step:.1f}" height="{H - T - B}"/>')
        for col, _, slot in KINDS:
            v = int(r[col])
            if v:
                # A 2px gap between segments so they read apart without relying on color.
                h = max(0.5, y(base) - y(base + v) - 2)
                out.append(f'<rect class="{slot}" x="{x:.1f}" y="{y(base + v):.1f}" width="{bw:.1f}" height="{h:.1f}"/>')
            base += v
        out.append("</g>")
        if r["month"].endswith(("-01", "-04", "-07", "-10")):
            out.append(f'<text class="axis" x="{x + bw / 2:.1f}" y="{H - 10}" text-anchor="middle">{month_label(r["month"])}</text>')
    out.append("</svg>")
    return "".join(out)


def chart_plaintiffs(rows: list[dict], top: int = 12) -> str:
    """Horizontal bars: the largest plaintiffs by cases filed. One series, so one color."""
    rows = rows[:top]
    W, RH, L = 880, 30, 250
    H = RH * len(rows) + 6
    xmax = int(rows[0]["cases"])
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="The {top} plaintiffs that filed the most debt claims">']
    for i, r in enumerate(rows):
        yy = 4 + i * RH
        w = (W - L - 90) * int(r["cases"]) / xmax
        tip = f"{r['plaintiff']} ({r['kind']}): {n(r['cases'])} cases, {r['pct_of_cases']}% of all; median claim ${n(r['median_claim'])}"
        out.append(f'<g class="bar" data-tip="{esc(tip)}"><rect class="hit" x="0" y="{yy - 2}" width="{W}" height="{RH}"/>'
                   f'<text class="name" x="{L - 10}" y="{yy + 16}" text-anchor="end">{esc(r["plaintiff"])}</text>'
                   f'<rect class="c1" x="{L}" y="{yy + 2}" width="{w:.1f}" height="{RH - 10}" rx="3"/>'
                   f'<text class="val" x="{L + w + 8:.1f}" y="{yy + 16}">{n(r["cases"])}</text></g>')
    out.append("</svg>")
    return "".join(out)


def chart_outcomes(rows: list[dict], label_col: str, count_col: str) -> str:
    """100% stacked bars: how cases ended, one bar per group."""
    W, RH, L = 880, 58, 0
    H = RH * len(rows)
    out = [f'<svg viewBox="0 0 {W} {H}" role="img" aria-label="How cases ended, by group">']
    for i, r in enumerate(rows):
        yy, x = i * RH, L
        out.append(f'<text class="name" x="0" y="{yy + 14}">{esc(r[label_col][0].upper() + r[label_col][1:])} '
                   f'<tspan class="axis">({n(r[count_col])} cases)</tspan></text>')
        for col, label, slot, ink in OUTCOMES:
            v = float(r[col])
            w = (W - L) * v / 100
            if w <= 0:
                continue
            out.append(f'<g class="bar" data-tip="{esc(label)}: {v}%"><rect class="{slot}" x="{x:.1f}" y="{yy + 22}" width="{max(0.5, w - 2):.1f}" height="26"/>')
            if w > 42:
                out.append(f'<text class="in" x="{x + 6:.1f}" y="{yy + 40}" style="fill:{ink}">{v:g}%</text>')
            out.append("</g>")
            x += w
    out.append("</svg>")
    return "".join(out)


def legend(items) -> str:
    return '<div class="legend">' + "".join(f'<span class="sw"><i class="{slot}"></i>{esc(label)}</span>' for label, slot in items) + "</div>"


def table(head: list[str], rows: list[list], numeric_from: int = 1) -> str:
    th = "".join(f'<th{" class=n" if i >= numeric_from else ""}>{esc(h)}</th>' for i, h in enumerate(head))
    body = "".join("<tr>" + "".join(f'<td{" class=n" if i >= numeric_from else ""}>{esc(c)}</td>' for i, c in enumerate(r)) + "</tr>" for r in rows)
    return f'<div class="scroll"><table><thead><tr>{th}</tr></thead><tbody>{body}</tbody></table></div>'


PAGE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Harris County Debt Docket</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Source+Serif+4:opsz,wght@8..60,600&family=IBM+Plex+Sans:wght@400;500;600&display=swap" rel="stylesheet">
<style>
:root {
  /* Layout: headline figures, then three charts top to bottom (when, who, how it ends), each with its table. */
  --bg: #f6f7f8; --surface: #ffffff; --ink: #1d2329; --muted: #5d6873; --line: #dde2e7; --accent: #8a2c1f;
  --c1: #2a78d6; --c2: #eb6834; --c3: #1baf7a; --c4: #eda100; --c5: #e87ba4; --open: #dfe3e7;
  --display: "Source Serif 4", Georgia, serif; --body: "IBM Plex Sans", system-ui, sans-serif;
  color-scheme: light;
}
@media (prefers-color-scheme: dark) { :root:not([data-theme="light"]) {
  --bg: #15191d; --surface: #1d2328; --ink: #e8ecef; --muted: #9aa5ae; --line: #2f373e; --accent: #f08c6e;
  --c1: #3987e5; --c2: #d95926; --c3: #199e70; --c4: #c98500; --c5: #d55181; --open: #39424a; color-scheme: dark; } }
:root[data-theme="dark"] {
  --bg: #15191d; --surface: #1d2328; --ink: #e8ecef; --muted: #9aa5ae; --line: #2f373e; --accent: #f08c6e;
  --c1: #3987e5; --c2: #d95926; --c3: #199e70; --c4: #c98500; --c5: #d55181; --open: #39424a; color-scheme: dark; }
* { box-sizing: border-box; }
html, body { margin: 0; background: var(--bg); color: var(--ink); font: 15px/1.5 var(--body); }
main { max-width: 1120px; margin: 0 auto; padding: 24px 16px 48px; display: grid; gap: 20px; }
h1 { font: 600 30px/1.15 var(--display); margin: 0; text-wrap: balance; }
h2 { font: 600 19px/1.25 var(--display); margin: 0 0 4px; text-wrap: balance; }
p { margin: 0; }
a { color: var(--accent); }
.lede { color: var(--muted); max-width: 68ch; margin-top: 6px; }
.sub { color: var(--muted); font-size: 14px; max-width: 78ch; margin-bottom: 12px; }
.panel { background: var(--surface); border: 1px solid var(--line); border-radius: 8px; padding: 16px; min-width: 0; }
.facts { display: flex; flex-wrap: wrap; gap: 14px 32px; }
.facts div { font-size: 13px; color: var(--muted); max-width: 22ch; }
.facts b { display: block; font: 600 26px/1.2 var(--display); color: var(--ink); font-variant-numeric: tabular-nums; }
svg { display: block; width: 100%; height: auto; overflow: visible; }
svg text { font: 12px var(--body); fill: var(--ink); }
svg text.axis, svg tspan.axis { fill: var(--muted); font-size: 12px; }
svg text.name { font-size: 13px; font-weight: 500; }
svg text.val { font-size: 13px; font-variant-numeric: tabular-nums; }
svg text.in { font-size: 12px; font-weight: 600; pointer-events: none; }
svg line.grid { stroke: var(--line); stroke-width: 1; }
svg rect.hit { fill: transparent; }
svg .bar:hover rect.hit { fill: var(--bg); }
.c1 { fill: var(--c1); background: var(--c1); } .c2 { fill: var(--c2); background: var(--c2); }
.c3 { fill: var(--c3); background: var(--c3); } .c4 { fill: var(--c4); background: var(--c4); }
.c5 { fill: var(--c5); background: var(--c5); } .open { fill: var(--open); background: var(--open); }
.legend { display: flex; flex-wrap: wrap; gap: 6px 16px; font-size: 13px; color: var(--muted); margin-bottom: 10px; }
.legend .sw { display: inline-flex; align-items: center; gap: 6px; }
.legend i { width: 14px; height: 14px; border-radius: 3px; display: inline-block; }
.wide { overflow-x: auto; } .wide svg { min-width: 640px; }
.scroll { overflow-x: auto; margin-top: 14px; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--line); white-space: nowrap; }
th { color: var(--muted); font-weight: 500; position: sticky; top: 0; background: var(--surface); }
td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
details summary { cursor: pointer; color: var(--accent); font-weight: 500; margin-top: 12px; }
.notes { color: var(--muted); font-size: 14px; }
.notes ul, .notes p { max-width: 86ch; }
.notes li { margin-bottom: 6px; }
#tip { position: fixed; z-index: 5; pointer-events: none; background: var(--ink); color: var(--surface); font-size: 13px;
  padding: 6px 9px; border-radius: 6px; max-width: 320px; display: none; }
</style>
</head>
<body>
<main>
  <header>
    <h1>The Harris County debt docket</h1>
    <p class="lede">Who files debt-collection lawsuits in the justice courts of Harris County, Texas (Houston), for how much, and how the cases end. From the county's public case records, __FIRST__ to __LAST__. No names or addresses of the people sued are collected. <a href="https://github.com/adamfriedl/justice-gap-map/blob/main/docs/lawsuits/README.md">Statewide filing counts for Texas, Indiana and Virginia</a></p>
  </header>

  <section class="panel facts">__FACTS__</section>

  <section class="panel">
    <h2>Debt claims filed each month</h2>
    <p class="sub">Cases filed, by the kind of company that filed them. __LASTFULL__ is the last full month shown.</p>
    __LEGEND_KINDS__
    <div class="wide">__CHART_MONTHS__</div>
    <details><summary>Show the numbers</summary>__TABLE_MONTHS__</details>
  </section>

  <section class="panel">
    <h2>Ten companies filed __TOP10__% of the cases</h2>
    <p class="sub">The __NPLAINTIFFS__ largest plaintiffs by cases filed, __FIRST__ to __LAST__. Company names are typed many ways in the records and are combined here; the lookup is in the repository.</p>
    <div class="wide">__CHART_PLAINTIFFS__</div>
    <details><summary>Show the 40 largest plaintiffs, with how their __Y__ cases ended</summary>__TABLE_PLAINTIFFS__</details>
  </section>

  <section class="panel">
    <h2>How cases filed in __Y__ ended, with and without an attorney for the defendant</h2>
    <p class="sub">Share of all cases filed in __Y__, as of __SNAPSHOT__. This describes the records. It doesn't show what an attorney changes: people who hire one differ from people who don't, and the field may miss help that never appears on the docket.</p>
    __LEGEND_OUTCOMES__
    <div class="wide">__CHART_REP__</div>
    <h2 style="margin-top:22px">The same, by kind of plaintiff</h2>
    <div class="wide">__CHART_KIND__</div>
    <details><summary>Show the numbers, and each court</summary>__TABLE_KIND____TABLE_COURT__</details>
  </section>

  <section class="panel notes">
    <h2>How to read this</h2>
    <ul>
      <li><b>One county, one kind of court.</b> Harris County's 16 justice courts hear the smaller claims. Larger debt suits go to county and district courts and aren't here.</li>
      <li><b>Courts move at different speeds.</b> In some courts most __Y__ cases are closed; in others most are still open. Outcome shares for a plaintiff partly reflect which courts it files in. The table above shows each court.</li>
      <li><b>Kinds of plaintiff are this project's grouping,</b> made from company names. It isn't from a registry and hasn't been checked against one. __UNCLASSIFIED__% of cases have a plaintiff that isn't classified.</li>
      <li><b>"Dropped by the plaintiff"</b> is the courts' category "non-suited or dismissed by plaintiff". The records don't say why a case was dropped.</li>
      <li><b>A case is counted once,</b> at its latest status in the county's extract downloaded __SNAPSHOT__. The county's count for __Y__ here is __COHORT__; the state's Office of Court Administration reports 91,823 debt claims filed in Harris County justice courts in __Y__, about 3% fewer.</li>
    </ul>
    <p style="margin-top:10px">Source: <a href="https://jpwebsite.harriscountytx.gov/PublicExtracts/search.jsp">Harris County Justice Courts public data extract</a>. Tables and code: <a href="https://github.com/adamfriedl/justice-gap-map/tree/main/docs/docket">docs/docket</a> in the repository.</p>
  </section>
</main>
<div id="tip" role="status"></div>
<script>
// Tooltip for the charts. Every figure is also in the tables.
const tip = document.getElementById("tip");
document.addEventListener("pointermove", e => {
  const g = e.target.closest && e.target.closest("[data-tip]");
  if (!g) { tip.style.display = "none"; return; }
  tip.textContent = g.dataset.tip; tip.style.display = "block";
  const w = tip.offsetWidth, x = Math.min(window.innerWidth - w - 8, e.clientX + 14);
  tip.style.left = Math.max(8, x) + "px"; tip.style.top = (e.clientY + 16) + "px";
});
document.addEventListener("pointerleave", () => { tip.style.display = "none"; });
</script>
</body>
</html>
"""


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tables", default="docs/docket")
    p.add_argument("--out", default="site/index.html")
    p.add_argument("--cohort", type=int, default=2025)
    a = p.parse_args()
    t, y = Path(a.tables), a.cohort
    s = {r["measure"]: r["value"] for r in read(t / "summary.csv")}
    months = read(t / "by_month.csv")
    last_month = s["last filing date"][:7]
    full = [m for m in months if m["month"] != last_month]  # the last month is partial
    plaintiffs = [r for r in read(t / "by_plaintiff.csv") if r["plaintiff"] != "All other plaintiffs"]
    outcomes = {r["plaintiff"]: r for r in read(t / f"outcomes_by_plaintiff_{y}.csv")}
    rep = read(t / f"outcomes_by_representation_{y}.csv")
    kinds = read(t / f"outcomes_by_kind_{y}.csv")
    courts = read(t / f"by_court_{y}.csv")

    def date(d: str) -> str:
        yy, mm, dd = d.split("-")
        return f"{month_label(yy + '-' + mm).split()[0]} {int(dd)}, {yy}"

    facts = [
        (n(s["cases"]), f"debt claims filed, {date(s['first filing date'])} to {date(s['last filing date'])}"),
        (s["share of cases filed by the 10 largest plaintiffs, percent"] + "%", "filed by the ten largest plaintiffs"),
        (s["share of cases filed by debt buyers, percent"] + "%", "filed by debt buyers, companies that buy unpaid accounts"),
        ("$" + n(s["median claim, dollars"]), "median amount claimed"),
        (f"${float(s['total claimed, dollars']) / 1e9:.2f} billion", "claimed in all"),
    ]
    oc_head = ["Default judgment", "Dropped by plaintiff", "Agreed judgment", "Dismissed, not pursued", "Trial or other", "Still open", "Defendant had attorney"]
    oc_cols = [c for c, *_ in OUTCOMES] + ["pct_defendant_had_attorney"]
    pl_rows = []
    for r in plaintiffs:
        o = outcomes.get(r["plaintiff"])
        pl_rows.append([r["plaintiff"], r["kind"], n(r["cases"]), r["pct_of_cases"] + "%", "$" + n(r["median_claim"]), n(r[f"cases_{y}"])]
                       + ([o[c] + "%" for c in oc_cols] if o else ["–"] * len(oc_cols)))
    fill = {
        "__FIRST__": date(s["first filing date"]), "__LAST__": date(s["last filing date"]), "__SNAPSHOT__": date(s["snapshot (latest download date)"]),
        "__Y__": str(y), "__COHORT__": n(s[f"cases filed in {y}"]), "__LASTFULL__": month_label(full[-1]["month"]),
        "__TOP10__": str(round(float(s["share of cases filed by the 10 largest plaintiffs, percent"]))),
        "__NPLAINTIFFS__": "12",
        "__UNCLASSIFIED__": s["share of cases whose plaintiff is not classified, percent"],
        "__FACTS__": "".join(f"<div><b>{esc(b)}</b>{esc(label)}</div>" for b, label in facts),
        "__LEGEND_KINDS__": legend([(label, slot) for _, label, slot in KINDS]),
        "__LEGEND_OUTCOMES__": legend([(label, slot) for _, label, slot, _ in OUTCOMES]),
        "__CHART_MONTHS__": chart_months(full),
        "__CHART_PLAINTIFFS__": chart_plaintiffs(plaintiffs, 12),
        "__CHART_REP__": chart_outcomes(rep, "group_name", f"cases_{y}"),
        "__CHART_KIND__": chart_outcomes(kinds, "kind", f"cases_{y}"),
        "__TABLE_MONTHS__": table(["Month", "Cases"] + [label for _, label, _ in KINDS] + ["Median claim"],
                                  [[month_label(m["month"]) + (" (to the " + str(int(s["last filing date"][8:])) + "th)" if m["month"] == last_month else ""),
                                    n(m["cases"])] + [n(m[c]) for c, *_ in KINDS] + ["$" + n(m["median_claim"])] for m in months]),
        "__TABLE_PLAINTIFFS__": table(["Plaintiff", "Kind", "Cases", "Share", "Median claim", f"Filed in {y}"] + oc_head, pl_rows, 2),
        "__TABLE_KIND__": table(["Kind of plaintiff", f"Filed in {y}", "Median claim"] + oc_head,
                                [[k["kind"], n(k[f"cases_{y}"]), "$" + n(k["median_claim"])] + [k[c] + "%" for c in oc_cols] for k in kinds]),
        "__TABLE_COURT__": table(["Court", f"Filed in {y}"] + oc_head,
                                 [[c["court"], n(c[f"cases_{y}"])] + [c[col] + "%" for col in oc_cols] for c in courts]),
    }
    page = PAGE
    for k, v in fill.items():
        page = page.replace(k, v)
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(page)
    print(f"wrote {out} ({len(page) // 1024} KB)")


if __name__ == "__main__":
    main()
