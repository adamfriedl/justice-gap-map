# Phase 0: do complaints measure need?

_Run 2026-11-06. Third Phase 0 check (after CFPB ZIP coverage and the crosswalk)._

## Verdict

- **CFPB complaints fail as the pressure measure.** In Texas, county complaint rates barely track debt-lawsuit filing rates (Spearman 0.24 across 66 larger counties). The poorest counties have the most debt in collections, the same lawsuit rate, and the fewest complaints. That's the pattern the PRD worried about.
- **An awareness-free measure is usable: the Urban Institute's county debt-in-collections share.** It downloads as CSV, covers 3,071 of 3,143 counties, and uses August 2025 credit data. **The PRD's pressure gate passes on this measure, not on complaints.**
- **The 2024–26 surge is partly batch filing and partly real.** Complaints per filer roughly rose by a third, and credit-bureau complaints jumped. Even counted once per filer per day, though, volume tripled, while Texas debt lawsuits grew 67% over the same period.

Recommendation: use debt in collections as the pressure measure. Keep complaints only as a secondary signal, for example the gap between debt in collections and complaints (PRD open question 4). Count complaints once per ZIP and day, rather than raw, wherever they're used.

## Sources

| Source | Snapshot | Where |
| --- | --- | --- |
| CFPB complaints CSV | Same file as the earlier checks: `Last-Modified: Fri, 06 Nov 2026 10:17:04 GMT`, downloaded 2026-11-06. 1,231,752 debt-collection complaints. | https://files.consumerfinance.gov/ccdb/complaints.csv.zip |
| HUD-USPS ZIP→county | 2026 Q2 | HUD API `type=2` |
| Urban Institute, Debt in America | Published 2025-11-20, credit bureau data from August 2025 (4% panel from one bureau). Files `Last-Modified: 19 Nov 2025`. | `https://apps.urban.org/features/debt-interactive-map/data/20251023-update/county_overall.csv`. The "Download data" link points to `datacatalog.urban.org/dataset/debt-america-2025`, which returns 403 to scripts, so the script pulls the CSVs the map itself loads. |
| Texas OCA Court Activity Reporting | "Justice Court Activity Detail" (HB79 period), one Excel file per county, calendar years 2023 and 2025, downloaded 2026-11-06 | https://card.txcourts.gov/ |
| ACS 2020–2024 5-year | County population, and population under 125% of poverty (C17002) | Census API |
| January Advisors (cross-check only) | "Consumer Debt Filings Kept Climbing in 2025", 2026-07-15 | https://www.januaryadvisors.com/consumer-debt-filings-kept-climbing-in-2025/ |

Reproduce:

```bash
scripts/phase0_download.sh            # CFPB + HUD (earlier check)
scripts/phase0_need_download.sh       # Urban + ACS
uv run python scripts/phase0_tx_courts_fetch.py --years 2023 2025   # ~1.5 h, 1 s between requests
uv run python scripts/phase0_need.py \
    --complaints data/cfpb/2026-11-06/complaints.csv --hud data/hud/zip_county_20262.json \
    --urban data/urban/2025-11-20/county_overall.csv --acs data/acs/county_acs5_2024.json \
    --tx data/txcourts/2026-11-06 --out docs/phase0/need
```

Every number below comes from the CSVs in [`need/`](need/), produced by `scripts/phase0_need.py`.

## Definitions

- **County complaint rate:** debt-collection complaints with a 5-digit ZIP, allocated to counties by HUD's residential ratio, per 10,000 residents. Complaints with masked ZIPs (about 10%, mostly rural) are dropped, so small-county rates run low (see the earlier check).
- **Same-day batch:** a complaint from a ZIP that sent complaints about 3 or more companies on the same day. **ZIP-day:** one ZIP on one day with at least one complaint. It's a rough count of filers, since one person filing several complaints at once counts once.
- **Debt in collections (`totcoll`):** Urban's "share of people with a credit bureau record who have any debt in collections." Collections include charged-off accounts and accounts more than 180 days past due ([technical appendix](https://apps.urban.org/features/debt-interactive-map/downloadable-docs/debt_interactive_technical_appendix_2025.pdf)). Urban suppresses counties with fewer than 50 people in its sample (shown as NA), and still uses Connecticut's pre-2022 counties, so Connecticut doesn't join.
- **Texas debt-claim filing rate:** new "Debt Claim" cases filed in justice courts, per 1,000 residents. Debt-claim cases are justice-court suits by assignees, debt collectors, lenders, and financial institutions. That definition comes from Texas Rule of Civil Procedure 508; I didn't re-check the rule text in this session (**not confirmed**). This count misses larger debt suits filed in county and district courts.
- **Reporting rate:** OCA reports what share of each county's expected monthly court reports arrived. The main Texas sample keeps counties at 90% or above. 225 of 254 counties qualify for 2025, covering 95.0% of the population. **Hidalgo County (pop. 892K) reported 0% in both 2023 and 2025**, so it's out.
- Correlations are Spearman (rank) correlations across counties. The main samples are counties with 50,000+ residents, where ZIP masking matters less.

## 1. Texas: complaints vs. debt lawsuits

Texas justice courts took **518,852 debt-claim filings in 2025**, up from 310,665 in 2023 (+67%). January Advisors reports 515,371 for 2025 from OCA's aggregate data, a close match. 33.6% of debt-claim dispositions in 2025 were default judgments. ([texas_summary.csv](need/texas_summary.csv), [texas_counties.csv](need/texas_counties.csv))

| Spearman correlation, 2025, larger counties (66) | ρ |
| --- | --- |
| Complaint rate vs. debt-claim filing rate | 0.24 |
| Same, excluding same-day batches | 0.18 |
| 2019–23 complaint rate vs. 2025 filing rate | 0.13 |
| 2023→2025 growth in filings vs. growth in complaints (62 counties) | −0.04 |
| Debt in collections vs. filing rate | 0.10 |
| Complaint rate vs. debt in collections | −0.18 |

([texas_correlations.csv](need/texas_correlations.csv))

Across all 225 fully reporting counties, the complaint–filing correlation rises to 0.45. That figure is probably inflated by masking: small rural counties lose their complaints to masking, and have fewer filings too, so they cluster at the bottom of both.

Lawsuit rates are fairly even across larger counties (coefficient of variation 0.22). Complaint rates vary four times as much (0.93), so something other than lawsuits drives most of the variation in complaints. Splitting the same 66 counties into thirds by poverty ([texas_by_poverty_third.csv](need/texas_by_poverty_third.csv)):

| Poverty third | Median % under 125% poverty | Median % with debt in collections | Debt filings per 1K | Default share | Complaints per 10K |
| --- | --- | --- | --- | --- | --- |
| Lowest | 12.5 | 27.9 | 18.9 | 35.0% | 8.6 |
| Middle | 16.3 | 34.9 | 18.1 | 35.7% | 8.3 |
| Highest | 21.1 | 38.0 | 19.0 | 37.1% | 5.7 |

The poorest counties get sued at the same rate, default slightly more, carry more debt in collections, and complain about a third less. The border counties are the clearest case: Cameron has 41% in collections and 19.5 filings per 1K but 4.3 complaints per 10K, and El Paso has 33%, 19.4, and 6.1.

**Result: complaints do not track lawsuits in Texas.** Debt in collections doesn't track lawsuit rates closely either (0.10). It measures exposure to collection, while filing rates also reflect plaintiffs' choices. Both describe pressure; neither stands in for the other.

## 2. National: complaints vs. debt in collections

Across 990 counties with 50,000+ residents ([national_correlations.csv](need/national_correlations.csv)):

| Spearman correlation with debt in collections | ρ | Ranked within each state |
| --- | --- | --- |
| 2025 complaint rate | 0.47 | 0.21 |
| 2019–23 average complaint rate | 0.30 | 0.10 |
| 2025 rate, excluding credit-bureau complaints | 0.46 | 0.23 |
| 2025 rate, excluding same-day batches | 0.44 | 0.19 |
| 2025 ZIP-days per 10K | 0.46 | 0.21 |

By tenths of counties ranked on debt in collections, the median 2025 complaint rate climbs from 1.8 per 10K in the lowest tenth to 11.4 in the highest ([national_by_collections_decile.csv](need/national_by_collections_decile.csv)). So nationally, complaints don't run opposite to debt in collections. But most of that link is between states, mainly the high-debt South against everyone else. Within a state, which is the comparison a map of service areas needs, it falls to about 0.2, and to 0.1 before the surge. Complaint rates barely relate to poverty (0.12). Debt in collections does (0.69).

## 3. The 2024–26 surge

([surge_by_year.csv](need/surge_by_year.csv), [surge_zip_days.csv](need/surge_zip_days.csv), [surge_top_companies.csv](need/surge_top_companies.csv), [surge_mix.csv](need/surge_mix.csv))

| | 2021 | 2023 | 2025 | 2026 (to Nov 6) |
| --- | --- | --- | --- | --- |
| Debt-collection complaints | 70,300 | 68,107 | 283,199 | 265,701 |
| Submitted via web | 95.9% | 96.9% | 99.2% | 99.3% |
| Against Equifax, TransUnion, or Experian | 5.6% | 9.4% | 24.9% | 7.8% |
| Debt type "I do not know" | 23.4% | 26.8% | 54.5% | 64.0% |
| Issue "took or threatened negative or legal action" | 7.2% | 9.9% | 17.2% | 22.0% |
| 5-digit-ZIP complaints in a same-day batch | 22.0% | 18.6% | 43.6% | 41.8% |
| ZIP-days | 44,052 | 44,359 | 138,402 | 136,690 |
| Complaints per ZIP-day | 1.40 | 1.33 | 1.84 | 1.81 |
| Placebo: complaints from the same ZIP a week later | 0.08 | 0.06 | 0.25 | 0.26 |

- **Channel says nothing.** Almost everything comes in through the web in every year, so the PRD's "compare by submission channel" test can't separate third-party filers. The CSV has no field marking third-party or representative submissions (**not confirmed** whether CFPB records this internally).
- **Batch-like filing grew.** Same-day clusters are far above the placebo, so they are mostly one filer sending several complaints at once. Their share more than doubled. The three credit bureaus went from 6,382 debt-collection complaints in 2023 to 70,641 in 2025, then fell back to 7.8% of the total in 2026. Complaints that don't name a debt type doubled. Both patterns fit template or credit-repair-style filing, but the data can't show who filed (**not confirmed**).
- **Part of the rise is real.** Counted once per ZIP and day, volume still tripled from 2023 to 2025. Complaints about legal action rose from 6,733 to 48,578. Texas debt filings rose 67%. January Advisors attributes much of the national lawsuit surge to LVNV Funding, and LVNV's servicer, Resurgent Capital Services, went from 3,350 complaints in 2023 to 17,554 in 2025.
- **The geography is stable.** County complaint rates before and during the surge correlate at 0.78 (larger counties). Filtering batches or credit-bureau complaints barely changes any correlation above. So the surge mostly scales the map up rather than reshuffling it.
- The whole database grew faster than debt collection: 1.29M complaints in 2023, 5.44M in 2025, mostly credit reporting. Debt collection's share fell from 5.3% to 5.2%, then 4.2% in 2026 (ad hoc query on the same CSV, not in the committed outputs).

**On the PRD's fallback:** a pre-2024 baseline isn't necessary for geography and would throw away the years that matter. If complaints are used, count ZIP-days or drop same-day batches, and don't compare levels across the 2023/2024 break.

## Caveats

- Texas is one state, with one court level. Justice courts cap claims at $20,000 (**not confirmed** in this session), so larger debt suits in county and district courts are missing.
- OCA counts are self-reported by courts. Partial reporters are excluded, not adjusted.
- Urban's measure comes from one bureau's 4% sample and covers only people with a credit record ("credit invisible" people are left out). It's a single snapshot (August 2025). Older vintages aren't in these files.
- Complaints are placed by the consumer's ZIP. Lawsuits are counted by the court's county. In Texas justice courts these usually coincide, because suits are filed where the defendant lives (**not confirmed**).
- All of this is descriptive. Nothing here says why complaints are low where debt is high. Lower awareness of the CFPB is one explanation, not a finding.

## Implications for the plan

- **Pressure gate: pass**, using debt in collections. Swap it in as the primary pressure metric: share with debt in collections, county level, weighted by population for service areas.
- Complaints become a secondary layer. The most useful version is probably the PRD's open question 4: places with high debt in collections and few complaints, where people may not be pushing back.
- Pin Urban's vintage the way the HUD quarter is pinned: `data/20251023-update/`, credit data August 2025. Urban updates irregularly, so check for a new vintage before Phase 3.
- OCA's Court Activity database is a usable court-side source for Texas, if a v2 wants lawsuits (PRD Phase 6).
- `card.txcourts.gov` and `www.januaryadvisors.com` were added to the environment allowlist this session. Add them to AGENTS.md's host list.
