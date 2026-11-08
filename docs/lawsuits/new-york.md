# New York: can the project count debt lawsuits by county?

_Checked 2026-11-08. Script: [`scripts/lawsuits_ny_check.py`](../../scripts/lawsuits_ny_check.py). Tables: [`new-york/`](new-york/)._

## Verdict: not yet

- **New York's court websites refuse automated access.** `www.nycourts.gov`, `ww2.nycourts.gov` (which redirects there), and `iapps.courts.state.ny.us` (WebCivil Local, the case lookup) all answer a script with HTTP 403 and a Cloudflare "Just a moment..." challenge page. The site itself refuses, not this project's network proxy. As with the ABA site in Phase 0, the project doesn't get around it.
- **The one machine-readable source has no debt category.** LSC's Baseline Court Statistics has New York for 2016–2021. But it counts all civil filings, not consumer credit cases, and only 42 of New York's 62 counties appear (below).
- **So New York can't be added the way Texas, Indiana and Virginia were.** It could be added by hand if the maintainer downloads New York's caseload reports in a browser and they turn out to break out consumer credit by court (**not confirmed**; see "What would change this").

## What LSC's Baseline Court Statistics holds for New York

Source: LSC Baseline Court Statistics, `bcs_dataset_2023-05-01.csv` ([LSC post](https://civilcourtdata.lsc.gov/research/our-work/baseline-court-statistics/), 2023-05-04). It's "data provided by courts," calendar years 2016–2021. Full table: [`new-york/bcs_case_types.csv`](new-york/bcs_case_types.csv).

| Courts | Counties | Civil case types |
| --- | --- | --- |
| New York City Civil Court | 5 (the boroughs) | civil, housing, small claims, commercial claims |
| Outside NYC, court type not given | 37 | civil, landlord and tenant, small claims, commercial (plus criminal, vehicle and parking) |

The 37 counties outside NYC are probably those with city or district courts. Town and village justice courts are probably missing; both points are **not confirmed**. Counties with no row include much of rural upstate New York.

**Civil filings by year** ([`new-york/bcs_civil_by_year.csv`](new-york/bcs_civil_by_year.csv)):

| Year | NYC Civil Court: civil | Outside NYC: civil |
| --- | ---: | ---: |
| 2016 | 223,810 | 67,069 |
| 2017 | 253,616 | 78,079 |
| 2018 | 283,987 | 86,492 |
| 2019 | 324,653 | 98,154 |
| 2020 | 216,951 | 77,259 |
| 2021 | 261,622 | 90,132 |

Consumer debt suits may be a large share of NYC Civil Court's civil filings, but this file doesn't separate them, and their share is **not confirmed**. So these totals can't stand in for debt suits. Virginia's broad "General Civil" category was usable only because it could be checked against LSC's true warrant-in-debt counts (Spearman 0.75). New York has no such check here.

The series also ends in 2021, before the Consumer Credit Fairness Act. That law took effect in 2022 (**not confirmed** the exact date). Filings reportedly fell sharply afterward (**not confirmed**). This file can't show that change.

## What would change this

1. **The maintainer downloads New York's caseload reports by hand.** That means the Unified Court System's annual reports and caseload statistics pages, opened in a browser. If they give consumer credit filings by court and year, and ideally defaults, they become a manual download like the others in [`docs/manual-downloads.md`](../manual-downloads.md). Check three things: whether "consumer credit" is its own category, whether it's by court or county, and which years it covers, especially both sides of 2022.
2. **New York State open data** (`data.ny.gov`). The project's network allowlist blocks it, so it wasn't checked whether the courts publish there (**not confirmed**). If it's worth a look, add `data.ny.gov` to the allowlist.
3. **Researchers' compilations.** New York consumer-advocacy groups have published consumer credit filing counts from court data (**not confirmed** which, and whether they're downloadable).

Until one of these works out, New York stays off the map. A blank state means no usable data, not no lawsuits.
