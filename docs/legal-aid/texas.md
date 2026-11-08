# Texas: where legal aid offices are, and where debt suits are filed

_Built 2026-11-08. Script: [`scripts/tx_legal_aid.py`](../../scripts/tx_legal_aid.py). Tables: [`texas/`](texas/)._

This is the one-state prototype from the plan: debt suits by county, set next to where legal aid has offices. It describes places, not the programs. Office lists come from each program's own website, and "office" means a location listed there.

## Verdict

- **Most debt suits are filed in counties that have a legal aid office.** In 2025, 81% of Texas debt suits were filed in the 43 counties with an office (413,502 of 511,984, counting counties with complete court reporting). Those counties hold 79% of Texans.
- **Distance isn't where the gap shows.** Counties farther from an office have fewer suits per resident, not more (Spearman −0.48 across 225 counties). The suburban counties with the highest filing rates sit 20 to 35 miles from an office in Dallas, Fort Worth, Austin or San Antonio.
- **Volume is where it shows.** Each of the state's three LSC service areas has 14 to 16 offices. But the number of debt suits per eligible resident differs by half:

| LSC service area | Counties | Offices | Eligible residents | 2025 debt suits | Suits per 1,000 eligible | Suits per office |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| TX-13 (East Texas and the upper Gulf Coast, incl. Houston) | 72 | 14 | 2,056,305 | 202,517 | 98.5 | 14,466 |
| TX-14 (North and West Texas, incl. Dallas–Fort Worth) | 114 | 15 | 1,495,430 | 180,115 | 120.4 | 12,008 |
| TX-15 (South and Southwest Texas, incl. San Antonio, Austin, El Paso) | 68 | 16 | 1,673,295 | 136,220 | 81.4 | 8,514 |

"Eligible residents" is LSC's count of people under 125% of poverty in the area. "Offices" counts listed locations; a location with a busy docket and one with a quiet one count the same. These are place comparisons: how many suits arrive in an area relative to the legal aid footprint there. They say nothing about how any program performs. Debt defense is one of many kinds of cases these programs take on.

## Distance bands

From [`texas/distance_bands.csv`](texas/distance_bands.csv). Distance is measured in a straight line from each county's Census internal point to the nearest office's city.

| Nearest office | Counties | Population | 2025 debt suits (complete reporting) | Median suits per 1,000 |
| --- | ---: | ---: | ---: | ---: |
| In the county | 43 | 24,004,860 | 413,502 | 18.4 |
| Under 50 miles | 151 | 5,742,120 | 93,943 | 15.7 |
| 50–99 miles | 59 | 438,526 | 4,534 | 10.2 |
| 100+ miles | 1 (Lipscomb) | 2,918 | 5 | 1.7 |

The median county without an office is 40 miles from one; the farthest is 115 miles away. Distance has almost no relationship to the share of people in poverty (Spearman 0.06, [`texas/checks.csv`](texas/checks.csv)).

The counties without an office that have the most suits are **Williamson** (11,621 in 2025; 26 miles from Austin), **Hays** (4,799; 23 miles from Austin), **Kaufman** (4,722; 31 miles from Dallas), **Johnson** (4,506; 28 miles from Fort Worth) and **Guadalupe** (4,141; 36 miles from San Antonio).

## Sources and method

- **Offices:** fetched 2026-11-08 from each LSC-funded Texas program's website.
  - [Lone Star Legal Aid](https://www.lonestarlegal.org/offices/): 14 offices, each with the counties it serves. Three office pages (Conroe, Galveston, Richmond) list no street address, so they're placed at the city.
  - [Legal Aid of NorthWest Texas](https://legalaidtx.org/locations/), now at legalaidtx.org: 15 offices, each with counties served.
  - [Texas RioGrande Legal Aid](https://www.trla.org/offices): 16 locations with addresses, including a help desk in the Nueces County courthouse. The Mercedes office is left out: the site says it houses administration only, with no attorneys or intake.
  - Full list: [`texas/offices.csv`](texas/offices.csv).
- **Locations:** each office is placed at its city's internal point from the Census 2024 Gazetteer (places), then assigned to the county containing that point, using the us-atlas 3.0.1 county outlines. Corpus Christi's point falls in the bay at that map resolution, so it's assigned to the nearest county (Nueces).
- **County points:** Census 2024 Gazetteer (counties).
- **Debt suits:** Texas OCA justice-court "Debt Claim" filings, 2025 ([docs/lawsuits](../lawsuits/README.md)). Rates and bands use counties with at least 90% of expected court reports.
- **Service areas and awards:** LSC, FY2025 ([docs/phase0/lsc-data](../phase0/lsc-data/)).

## Caveats

- **An office list isn't capacity.** It leaves out staff counts, phone and online intake (each program lists an intake phone number with LSC), outreach sites, pro bono programs, and legal aid organizations that don't get LSC funding. Distance to a building matters less when intake is by phone. Court is still in person, though, and most debt cases end in default.
- **Straight-line miles from a county's center point** are rough. Real travel time differs, especially across big West Texas counties.
- **Debt defense is a small part of what legal aid does.** Suits per office measures the size of the docket in an area, not demand on any program. Whether programs take debt cases at all, and how many, is **not confirmed** here.
- **One year, one state.** Other states' offices aren't collected yet.

## What this suggests for the map

Distance to an office won't make a strong map layer for Texas: offices are where the suits are. The more useful comparison is volume relative to legal aid's footprint (suits per eligible resident and per office, by area), shown as place facts. Indiana and Virginia would need the same office collection to compare.
