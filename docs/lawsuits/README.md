# Where debt lawsuits are filed: Texas, Indiana, Virginia

_Built 2026-11-07. This is the project's lawsuit-first track: county counts of debt-collection suits in states whose courts publish them. Debt in collections (Urban) stays as national context._

## What's here

| File | What |
| --- | --- |
| [county_filings_tx_in.csv](county_filings_tx_in.csv) | Texas and Indiana, county × year: new debt suits, default judgments, cases disposed, filings per 1,000 residents, default share, poverty share, debt in collections |
| [virginia_courts_2025.csv](virginia_courts_2025.csv) | Virginia, per General District Court, 2025: General Civil filings, garnishments, landlord/tenant, and LSC's 2016–2019 warrant-in-debt average for comparison |
| [state_trend.csv](state_trend.csv) | Statewide filings and default share by year: Texas 2014–2025, Indiana 2014–2024 |
| [checks.csv](checks.csv) | Rank correlations (Spearman) behind the statements below |

Reproduce:

```bash
uv run python scripts/phase0_tx_courts_fetch.py --years 2019 2023 2024 2025      # county files, slow (~10-20 s each)
uv run python scripts/phase0_tx_courts_fetch.py --statewide --years 2014 2015 2016 2017 2018 2019 2020 2021 2022 2023 2024 2025
uv run python scripts/lawsuits_fetch_indiana.py --years 2014 2024
curl -o data/vacourts/2026-11-07/gdc_filings.pdf https://www.courts.state.va.us/static/courtadmin/aoc/djs/programs/cpss/csi/stats/gdc_filings.pdf
uv run python scripts/lawsuits.py --out docs/lawsuits
uv run python scripts/lawsuits_map.py --atlas data/atlas/package/counties-albers-10m.json   # us-atlas@3.0.1 from npm
```

## Sources and definitions

- **Texas:** new "Debt Claim" cases in justice courts, by calendar year, from OCA's Court Activity Reporting database (card.txcourts.gov), downloaded 2026-11-06 and 2026-11-07.
  - Debt claims are suits by debt buyers, collectors, and lenders (Texas Rule of Civil Procedure 508; **not confirmed** in this session). Larger suits in county and district courts aren't counted.
  - Counties whose courts sent fewer than 90% of expected monthly reports are excluded from county comparisons. Hidalgo County reported nothing.
  - The case type began in September 2013, so 2014 is the first full year.
- **Indiana:** new "Collection" (CC) cases in all courts in the county, from Indiana Court Online Reports (publicaccess.courts.in.gov/ICOR), downloaded 2026-11-07.
  - Small claims (SC) also contain debt suits but aren't separated. They're kept as `small_claims_filed`.
- **Virginia:** "General Civil & Civil Commitments" filings in General District Court, 2025, from the court system's monthly filing report (PDF, generated 2026-10-05).
  - Most are warrants in debt, but the category also holds other civil cases (the share is **not confirmed**).
  - The 2025 rates rank localities much like LSC's true warrant-in-debt counts for 2016–2019 did (Spearman 0.75, 121 courts).
  - Some courts serve several localities (e.g. Prince William with Manassas and Manassas Park), so those localities share one rate.
  - Fairfax City reports 0 General Civil cases, probably because they're heard in Fairfax County's court (**not confirmed**).
- **Default share:** default judgments ÷ cases disposed, same year.
- **Rates:** per 1,000 residents, using the ACS 2020–2024 5-year population.
- **Where a suit is counted:** at the court where it's filed. In all three states that's usually the defendant's county, but venue rules allow exceptions (**not confirmed**). Small cities with very high Virginia rates (Petersburg 198 per 1K, Fredericksburg 157) may reflect where plaintiffs file, not only where defendants live.

## What it shows

**Debt suits are surging in both states with a time series** ([state_trend.csv](state_trend.csv)).
- Texas justice courts: 106,061 debt claims in 2014, 326,471 in 2019, a pandemic dip, then 389,891 in 2024 and 518,852 in 2025 (+33% in one year). Default judgments grew from 21,325 to 136,163.
- Indiana collection cases: 67,683 in 2014, 92,343 in 2023, then 140,846 in 2024 (+53% in one year).

**Most cases end in default, more so in Indiana.**
- Indiana: 68% of collection cases disposed in 2024 ended in default judgments, up from 59% in 2014. The county median is 69%; St. Joseph County is 78.5% and Marion 75%.
- Texas: 33.6% in 2025. That isn't directly comparable, because many Texas debt claims end with the plaintiff non-suiting or dismissing (124,106 in FY2025 statewide, per OCA's annual report).

**Highest filing rates** (counties of 50K+, filings per 1,000 residents):
- **Texas 2025:** Kaufman 27.4, Ellis 25.8, Brazoria 24.4, Hunt 23.4, Taylor 23.4. Mostly suburban and exurban counties around Dallas–Fort Worth and Houston. County median 15.3.
- **Indiana 2024:** Marion (Indianapolis) 29.1, Lake (Gary) 29.0, Howard (Kokomo) 25.5, Madison (Anderson) 25.4, St. Joseph (South Bend) 23.5. County median 18.4.
- **Virginia 2025 (General Civil):** Hampton 100.8, Richmond City 95.4, Lynchburg 73.2, Roanoke City 72.2, Newport News 64.9, Norfolk 64.3. Older cities, mostly Hampton Roads and Southside. Locality median 41.8.

**What filing rates track** ([checks.csv](checks.csv)):

| Comparison (Spearman across counties) | Texas | Indiana | Virginia |
| --- | --- | --- | --- |
| Filings vs. share in poverty (under 125%) | −0.03 (2025) | 0.14 (2024) | 0.44 (2025) |
| Filings vs. debt in collections (Urban) | 0.15 | 0.59 | — |
| Filings, early year vs. latest year | 0.53 (2019 vs 2025), 0.71 (2023 vs 2025) | 0.62 (2014 vs 2024) | 0.75 (2016–19 warrants vs 2025 General Civil) |


So:
- The places with the most suits stay fairly consistent over time.
- How filing rates relate to poverty and debt differs a lot by state. In Indiana and Virginia, suits concentrate where debt and poverty are higher. In Texas they don't: the fast-growing suburban counties lead, and the poor border counties are middling.
- One measure won't stand in for another. Where lawsuits matter, you need the court data itself.

## Caveats

- Three states, three different case definitions. Compare places within a state. Across states, compare trends, not levels.
- Texas misses county- and district-court debt suits. Indiana misses debt suits filed as small claims. Virginia's category is broader than debt.
- All counts are what courts report to their state; partial reporting is excluded, not adjusted.

## Next states to add

LSC's Baseline Court Statistics (2023) shows county debt case types for Idaho (creditor/debtor collections, courtdata.idaho.gov dashboard), Iowa, Alaska, Arkansas (to 2018), and Florida (contract and indebtedness, which mixes in business contracts). Idaho's dashboard is the most promising live source. New York was checked on 2026-11-08 and can't be added yet: its court sites refuse scripts, and LSC's file has no debt category for it ([new-york.md](new-york.md)). Missouri, Minnesota, and North Dakota are tracked case-by-case by the Debt Collection Lab and January Advisors, but whether that data can be downloaded is **not confirmed**.
