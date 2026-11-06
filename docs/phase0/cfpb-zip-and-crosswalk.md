# Phase 0: CFPB ZIP coverage and HUD crosswalk match

_Run 2026-11-06. CFPB and crosswalk only; LSC and the gap check are still open._

## Sources and snapshot

| Source | Snapshot | Where |
| --- | --- | --- |
| CFPB complaints CSV | `complaints.csv.zip`, server `Last-Modified: Fri, 06 Nov 2026 10:17:04 GMT`, downloaded 2026-11-06. 18,965,764 rows, date received 2011-12-01 to 2026-11-06. | https://files.consumerfinance.gov/ccdb/complaints.csv.zip |
| HUD-USPS ZIP→county crosswalk | API `type=2`, **2026 Q2** (2026 Q3 returned an error, so Q2 is the latest available on 2026-11-06) | `https://www.huduser.gov/hudapi/public/usps?type=2&query=All&year=2026&quarter=2` |

Reproduce:

```bash
scripts/phase0_download.sh
uv run python scripts/phase0_cfpb_zip.py --complaints data/cfpb/2026-11-06/complaints.csv --hud data/hud/zip_county_20262.json --out docs/phase0
```

Every number below comes from the CSVs in this folder, produced by that script.

## Definitions

- **Scope:** `Product = 'Debt collection'`: 1,231,752 complaints, all with unique Complaint IDs, dated 2013–2026. The separate `Debt or credit management` product (10,861 rows) is excluded.
- **ZIP class**, following the CFPB field reference ([fields.html](https://cfpb.github.io/api/ccdb/fields.html)): `zip5` is five digits; `zip3` is published as `123XX`; `none` is everything else. In this file "none" was `XXXXX` (15,080), blank (475), and 12 malformed values like `2011-`.
- **County-placeable:** a `zip5` that appears in the HUD 2026 Q2 ZIP→county file.

CFPB's masking rule, as its docs state it: the 5-digit ZIP is published unless the ZIP's Census ZCTA has fewer than 20,000 people; then the 3-digit ZIP is published if the 3-digit ZCTA has more than 20,000 people; otherwise nothing ([fields.html](https://cfpb.github.io/api/ccdb/fields.html)). The [data-use page](https://www.consumerfinance.gov/complaint/data-use/) adds that ZIP is blank for non-numeric submissions and non-U.S. addresses. The two pages word the threshold slightly differently ("fewer than 20,000" for the ZCTA vs. "less than 20,000 people in a given ZIP code").

## Findings

**1. Most complaints can be placed in a county: 89.5%.** That clears the PRD's ~70% bar comfortably. ([zip_class_overall.csv](zip_class_overall.csv))

| ZIP class | Share of debt-collection complaints |
| --- | --- |
| 5-digit | 89.62% |
| 3-digit | 9.12% |
| None | 1.26% |
| County-placeable (5-digit and in HUD) | 89.48% |

**2. The crosswalk is not the bottleneck.** 99.84% of complaints with a 5-digit ZIP match HUD 2026 Q2. By distinct ZIP the match is 96.3% (22,436 of 23,292); the unmatched ZIPs are mostly small (the largest has 55 complaints), and include military (`09xxx`, `96xxx`), `00000`, and PO-box or retired ZIPs. Only 0.1% of matched complaints carry a state that disagrees with HUD's state for that ZIP. ([crosswalk_match_overall.csv](crosswalk_match_overall.csv), [crosswalk_unmatched_top_zips.csv](crosswalk_unmatched_top_zips.csv))

**3. Most matched ZIPs sit in one county.** 74.5% of matched complaints are in a ZIP that lies wholly in one county, and 93.0% are in a ZIP with at least 90% of its residential addresses in one county. Allocating the rest by HUD's `res_ratio` is routine.

**4. Masking is uneven, and it hits rural states hardest.** Big, dense states are 92–95% placeable (CA 95.0%, NV 95.9%, TX 92.0%, FL 92.0%). The lowest are VT 57.1%, ME 62.1%, NH 72.8%, WV 73.6%, AK 73.6%, MT 74.9%, WY 75.3%, SD 75.7%, IA 77.2%, KS 77.7%, NE 78.2%, AL 78.6%. Only VT and ME fall below 70%. ([zip_class_by_state.csv](zip_class_by_state.csv))

This is the caveat that matters most for this project. Masked complaints come from ZIPs under 20,000 people, so dropping them **undercounts complaints in rural counties**, which is often where legal aid is thinnest. A naive county complaint rate would understate rural need.

**5. 3-digit complaints can't just be assigned to one county.** Only 7.2% of 3-digit complaints fall in a 3-digit prefix that covers a single county (HUD 2026 Q2). They need to be apportioned, or analyzed at the 3-digit level.

**6. Coverage by year.** ([zip_class_by_year.csv](zip_class_by_year.csv), [zip_class_by_state_year.csv](zip_class_by_state_year.csv))

| Year | Complaints | County-placeable |
| --- | --- | --- |
| 2013 | 11,068 | 98.8% |
| 2014 | 39,032 | 99.1% |
| 2015–2023 | 40K–70K a year | 84.5%–89.4% |
| 2024 | 155,894 | 88.4% |
| 2025 | 283,199 | 89.9% |
| 2026 (to Nov 6) | 265,701 | 93.0% |

Two oddities, both **not confirmed**:

- 2013–2014 complaints have no 3-digit ZIPs at all (0.0%). It looks like masking wasn't applied to the earliest records, but I found nothing in CFPB's docs that says so.
- The 3-digit share drops to 6.2% in 2026, from ~11–12% in 2016–2023. That could be a change in who complains, in CFPB's masking (for example, newer Census population figures), or something else.

Debt-collection volume roughly quadrupled from 2023 to 2025. That's descriptive only; it doesn't establish more harm, and might reflect more awareness or more filing through third parties.

## Other things noticed

- **No narrative column.** The CSV has 15 columns, and the current [field reference](https://cfpb.github.io/api/ccdb/fields.html) doesn't list `Consumer complaint narrative`, `Consumer consent provided?`, or `Consumer disputed?` either. Earlier releases of this dataset included narratives (the PRD assumes so); when and why they were dropped is **not confirmed**. Phase 0 doesn't need them, but it's another reason to start the archive (Goal 3) early.
- Territories and military: AE/AP/AA (military mail) are essentially unplaceable, as expected. PR is 85.9% placeable; VI and GU are around 52–58%. LSC funds programs in some territories, so decide whether they're in scope.
- 5,656 complaints have no state; 94% of those also have no ZIP.

## Implications for the plan

- **CFPB passes the Phase 0 bar.** County-level placement works for ~90% of debt-collection complaints. County is a viable unit, and service areas built from counties would inherit that.
- **Handle masking, don't just drop it.** Recommended approach for Phase 4: apportion each 3-digit complaint across the ZIPs in its prefix that CFPB would have masked (ZCTAs under 20K people, using ACS ZCTA populations), then to counties by HUD `res_ratio`. Report rates with and without the apportioned complaints so a reader can see the effect.
- **R6's data-quality report** should include the by-state placeable share from this script on every run.
- **Pin the crosswalk quarter.** Use the HUD quarter nearest each snapshot and record it, as done here.
