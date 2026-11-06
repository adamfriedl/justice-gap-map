"""Phase 0: downloads for the "Does LSC funding measure capacity?" check.

Everything lands under data/ (gitignored):

- IRS Exempt Organizations Business Master File, eo1-eo4.csv (all regions)
- LSC "By the Numbers" 2025 report (PDF, hosted on LSC's Box account)
- LSC's grantee list page (https://www.lsc.gov/about-lsc/our-grantees)
- LSC's one-page state profiles (PDF per state, from the public State Profiles
  page of https://www.lscdataease.org/, which links a Box folder per state)

    uv run python scripts/phase0_capacity_fetch.py

Stdlib only. The Box folder links come from the DataEase app's JavaScript
bundle, so they are read fresh each run; if LSC rebuilds the app, this step
may need updating.
"""

import argparse
import datetime as dt
import json
import re
import time
import urllib.request
from pathlib import Path

UA = {"User-Agent": "justice-gap-map research (Python urllib)"}
BTN_2025 = ("9mhek9c17vdb3x72cmkrbxkv7i74821e", "f_2376558870630")  # Box shared name, file id


def get(url: str) -> bytes:
    with urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=300) as r:
        return r.read()


def box_file(shared_name: str, file_id: str) -> bytes:
    return get("https://lsc-live.app.box.com/index.php?rm=box_download_shared_file"
               f"&shared_name={shared_name}&file_id={file_id}")


def state_profile_folders() -> dict[str, str]:
    """State FIPS -> Box shared-folder name, from the DataEase State Profiles page code."""
    index = get("https://www.lscdataease.org/").decode("utf-8", "ignore")
    for js in re.findall(r'href="(/js/chunk-[^"]+\.js)"', index):
        code = get("https://www.lscdataease.org" + js).decode("utf-8", "ignore")
        if "StateProfilesWeb" not in code:
            continue
        m = re.search(r'\{"01":"https://lsc-live\.box\.com/s/[^}]+\}', code)
        if m:
            pairs = re.findall(r'"?(\d+)"?:"https://lsc-live\.box\.com/s/([a-z0-9]+)"', m.group(0))
            return {k.zfill(2): v for k, v in pairs}
    raise RuntimeError("state profile folder links not found in the DataEase bundle")


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--snap", default=f"{dt.date.today():%Y-%m-%d}")
    p.add_argument("--pause", type=float, default=0.5)
    a = p.parse_args()

    irs = Path("data/irs") / a.snap
    irs.mkdir(parents=True, exist_ok=True)
    for i in range(1, 5):
        path = irs / f"eo{i}.csv"
        if not path.exists():
            path.write_bytes(get(f"https://www.irs.gov/pub/irs-soi/eo{i}.csv"))
    print(f"IRS BMF -> {irs}")

    lsc = Path("data/lsc") / a.snap
    lsc.mkdir(parents=True, exist_ok=True)
    (lsc / "btn2025.pdf").write_bytes(box_file(*BTN_2025))
    (lsc / "our-grantees.html").write_bytes(get("https://www.lsc.gov/about-lsc/our-grantees"))

    profiles = lsc / "state_profiles"
    profiles.mkdir(exist_ok=True)
    folders = state_profile_folders()
    (profiles / "folders.json").write_text(json.dumps(folders, indent=1))
    for fips, shared in sorted(folders.items()):
        if (profiles / f"{fips}.pdf").exists():
            continue
        found = None
        # The folder lists the state profile plus one per congressional district;
        # big states spill onto later pages of the folder listing.
        for page_no in range(1, 6):
            page = get(f"https://lsc-live.app.box.com/s/{shared}?page={page_no}").decode("utf-8", "ignore")
            hits = re.findall(r'"id":(\d+)[^{}]{0,400}?"name":"(![^"]*state_profile\.pdf)"', page)
            if hits:
                found = ("f_" + hits[0][0], hits[0][1])
                break
            if f"page={page_no + 1}" not in page and '"pageCount"' not in page:
                break
        if not found:
            print(f"{fips}: no state profile in folder")
            continue
        file_id, name = found
        (profiles / f"{fips}.pdf").write_bytes(box_file(shared, file_id))
        print(f"{fips}: {name}")
        time.sleep(a.pause)


if __name__ == "__main__":
    main()
