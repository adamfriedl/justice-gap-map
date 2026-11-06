"""Phase 0: download Texas justice-court activity by county from OCA's Court
Activity Reporting database (https://card.txcourts.gov/).

Uses the "Justice Court Activity Detail" report (HB79 period, 9/2013 on),
exported to Excel, one file per county per calendar year. Raw files land under
data/txcourts/<download date>/ (gitignored). Stdlib only.

    uv run python scripts/phase0_tx_courts_fetch.py --years 2023 2025

The site is an ASP.NET form, so each report takes a few postbacks. Requests are
spaced out (--pause) to go easy on the state's server.
"""

import argparse
import datetime as dt
import html
import http.cookiejar
import re
import time
import urllib.parse
import urllib.request
from pathlib import Path

BASE = "https://card.txcourts.gov/"
CRITERIA = "ReportCriteria.aspx?ddlReportName=134&ddlReportType=5020&ddlReportPeriod=HB79"


class Card:
    def __init__(self):
        jar = http.cookiejar.CookieJar()
        self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
        self.op.addheaders = [("User-Agent", "justice-gap-map research (Python urllib)")]

    def _read(self, path, data=None):
        body = urllib.parse.urlencode(data).encode() if data is not None else None
        with self.op.open(BASE + path, body, timeout=600) as r:
            return r.read(), r.headers

    def get(self, path):
        return self._read(path)[0].decode("utf-8", "ignore")

    def post(self, path, page, data, raw=False):
        form = hidden_fields(page)
        form.update(data)
        content, headers = self._read(path, form)
        return (content, headers) if raw else content.decode("utf-8", "ignore")


def hidden_fields(page):
    out = {}
    for tag in re.findall(r'<input[^>]*type="hidden"[^>]*>', page):
        name = re.search(r'name="([^"]+)"', tag)
        value = re.search(r'value="([^"]*)"', tag)
        if name:
            out[name.group(1)] = html.unescape(value.group(1) if value else "")
    return out


def counties(page):
    block = re.search(r'name="ddlCountyPostBack".*?</select>', page, re.S).group(0)
    return [(v, html.unescape(n).strip()) for v, n in re.findall(r'value="([^"]*)"[^>]*>([^<]*)', block) if v != "0"]


def criteria_page(card):
    t = card.get("ReportSelection.aspx")
    t = card.post("ReportSelection.aspx", t, {"__EVENTTARGET": "ddlReportType", "ddlReportType": "5020"})
    t = card.post("ReportSelection.aspx", t, {"__EVENTTARGET": "ddlReportName", "ddlReportType": "5020", "ddlReportName": "134"})
    return card.post("ReportSelection.aspx", t, {
        "ddlReportType": "5020", "ddlReportName": "134", "ddlReportPeriod": "HB79", "cmdContinue": "Continue"})


def fetch(card, year, county):
    """One county, January 1 to December 31 of `year`, as Excel bytes."""
    y = str(year)
    base = {"chkFrom": "on", "chkTo": "on", "ddlFormat": "1625", "ddlPrecinct": "0", "ddlPlace": "0",
            "ddlFromYear": y, "ddlToYear": y}
    t = criteria_page(card)
    # Each dropdown change is a postback that rebuilds the next one's options.
    t = card.post(CRITERIA, t, {**base, "__EVENTTARGET": "ddlFromYear", "ddlFromMonth": "9", "ddlToMonth": "9", "ddlCountyPostBack": "0"})
    t = card.post(CRITERIA, t, {**base, "__EVENTTARGET": "ddlToYear", "ddlFromMonth": "1", "ddlToMonth": "9", "ddlCountyPostBack": "0"})
    t = card.post(CRITERIA, t, {**base, "__EVENTTARGET": "ddlCountyPostBack", "ddlFromMonth": "1", "ddlToMonth": "12", "ddlCountyPostBack": county})
    content, headers = card.post(CRITERIA, t, {**base, "__EVENTTARGET": "btnRunReport", "ddlFromMonth": "1",
                                               "ddlToMonth": "12", "ddlCountyPostBack": county}, raw=True)
    if "excel" not in (headers.get("Content-Type") or ""):
        raise RuntimeError(f"unexpected response for county {county} {year}: {headers.get('Content-Type')}")
    return content


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--years", type=int, nargs="+", default=[2025])
    p.add_argument("--out", default=f"data/txcourts/{dt.date.today():%Y-%m-%d}")
    p.add_argument("--pause", type=float, default=1.0)
    a = p.parse_args()

    card = Card()
    county_list = counties(criteria_page(card))
    print(f"{len(county_list)} counties")
    for year in a.years:
        out = Path(a.out) / str(year)
        out.mkdir(parents=True, exist_ok=True)
        for value, name in county_list:
            path = out / f"{int(value):03d}_{name.replace(' ', '_')}.xls"
            if path.exists() and path.stat().st_size > 0:
                continue
            for attempt in range(4):
                try:
                    path.write_bytes(fetch(card, year, value))
                    break
                except Exception as e:  # network hiccups on a long run
                    print(f"retry {name} {year}: {e}")
                    time.sleep(2 ** (attempt + 1))
                    card = Card()
            time.sleep(a.pause)
        print(f"{year}: done -> {out}")


if __name__ == "__main__":
    main()
