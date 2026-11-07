# Phase 0: preliminary literature and prior-work scan

_Run 2026-11-07, in a cloud session, at the maintainer's request. **Preliminary.** Google Scholar and SSRN block automated access and weren't searched, so the PRD's full gap check still needs the maintainer. Method: about a dozen web searches, then reading the closest hits directly where the site allowed it._

## Bottom line

**I found no published work combining consumer-debt pressure with legal aid capacity at the county or service-area level.** Each half has been done separately, some of it well. The nearest neighbors are below. Two of them change the plan:

1. **LSC itself is moving toward this.** Its Civil Court Data Initiative (CCDI) collects court records from 900+ counties in 20 states, geocodes them "to identify the concentration of civil legal issues in low-income communities," and has published a Virginia debt-collection representation study (2025-01-08). It has published no national debt-versus-legal-aid map yet (as of 2026-11-07). The risk is overlap; the opportunity is partnership. LSC's data office should be one of the Phase 5 reviewers, and probably an early conversation.
2. **Using complaints as a need measure has a known flaw beyond awareness.** A 2020 *American Politics Research* article finds that legal aid and housing-counseling offices are associated with *more* CFPB complaints nearby. A gap score built on complaints would partly measure legal aid presence, and so could point away from the places with the least help. This supports the complaints check's decision to drop complaints as the pressure measure.

## What exists

| Work | What it does | Overlap with this project |
| --- | --- | --- |
| **LSC Civil Court Data Initiative** ([about](https://civilcourtdata.lsc.gov/about/project/), [our work](https://civilcourtdata.lsc.gov/research/our-work/)) | Court records from "over 900 counties in 20 states … over 20 million civil cases filed since 2016." It runs an eviction tracker. [Legal Representation in Virginia: Debt Collection and Eviction Cases](https://civilcourtdata.lsc.gov/research/our-work/va-2023-eviction-and-debt/) (2025-01-08) found 2.5M debt cases in 2018–2023, with consumers represented in 2% of them and 11× more likely to win when represented. | **High potential.** Court-side need measured by LSC itself. Not combined with funding or service areas in anything published. |
| **LSC Baseline Court Statistics dataset** ([post](https://civilcourtdata.lsc.gov/research/our-work/baseline-court-statistics/), 2023-05-04) | County-level civil filing counts from annual court reports, 39 states and territories. CSV on LSC's Box (`bcs_dataset_2023-05-01.csv`). | **A data source, not a competitor.** Case types aren't harmonized. In a quick look, 7 states have explicit debt categories (AK, AR, FL, ID, IA, VA, WI), through 2018–2022, and more have "collection" or "contract" types. It could repeat the Texas complaints-vs-lawsuits test in other states. |
| **LSC Justice Gap 2022** ([report](https://justicegap.lsc.gov/resource/2022-justice-gap-report/)) | National survey: 92% of low-income Americans' substantial civil legal problems get no or not enough legal help. | National only. It's the reason the project exists, not a local map. |
| **CFPB Complaint Bulletin, county-level demographics** ([report](https://www.consumerfinance.gov/data-research/research-reports/complaint-bulletin-county-level-demographic-overview-complaints/), April 2021) | Placed 2019–2020 complaints in counties using consumers' full mailing addresses. Per-capita complaint rates were over 4× higher in the most-minority counties than in the least-minority counties. | Same county-rate idea, using CFPB's internal addresses. No legal aid side. Its finding cuts against a simple "minority counties complain less" story; the Texas border-county result here is about Hispanic, high-poverty counties specifically. |
| **Raval (FTC), "Which Communities Complain to Policymakers? Evidence from Consumer Sentinel"** ([working paper](https://deveshraval.github.io/complaintSentinel.pdf), 2019), and ["Whose Voice Do We Hear in the Marketplace?"](https://deveshraval.github.io/complaintBehavior.pdf) | Complaint rates rise with education, and with income to a lesser degree. Heavily minority areas complain at much lower rates *relative to how often they're victimized*. An FTC slide deck also reports lower rates in Hispanic and rural areas. | **Strong support for the awareness-bias finding.** Cite it in the write-up. |
| ***American Politics Research* article on which constituencies file CFPB complaints**, 2020 ([DOI 10.1177/1532673X20962414](https://doi.org/10.1177/1532673X20962414); title and authors **not confirmed**, full text not read; described from search-result summaries) | Five years of complaints: they track middle- and upper-income mortgage holders. Legal aid offices and housing counselors are associated with more local complaints. | **Directly relevant caution** (see bottom line). |
| **Urban Institute, Debt in America** ([map](https://apps.urban.org/features/debt-interactive-map/)) | County debt in collections, August 2025. | The pressure measure. No legal aid layer. |
| **Debt Collection Lab** (Princeton), e.g. [How State Policies Affect Court Judgments](https://debtcollectionlab.org/research/how-state-policies-affect-court-judgments/) and [The Unequal Burden of Debt Claims](https://debtcollectionlab.org/docs/unequal-burden-of-debt-claims.pdf) (California) | Lawsuit tracker. Represented defendants are about 91% less likely to get a default judgment. The California study looks at where collectors sue by county demographics, and notes that legal aid's limited-scope help doesn't show up in court data. | Lawsuit side, a few states. The California report is the closest to "debt and legal aid in one place," but it doesn't map capacity. |
| **January Advisors** ([2025 update](https://www.januaryadvisors.com/consumer-debt-filings-kept-climbing-in-2025/)) | Lawsuit trends in 8 states and 9 metros, with LVNV's role. | Lawsuit trends only. |
| **Pew** ([2020 report](https://www.pew.org/en/research-and-analysis/reports/2020/05/how-debt-collectors-are-transforming-the-business-of-state-courts), [2024 state-law brief](https://phlr.org/sites/default/files/uploaded_images/PEW%20Debt%20Collection%20Policy%20Brief_Feb2024.pdf)) | More than 70% of debt cases end in default, and fewer than 10% of defendants have counsel. | Background, already cited in the PRD. |
| **ABA ABArray** ([page](https://www.americanbar.org/groups/legal_services/abarray-national-legal-aid-funding-data/)) | State civil legal aid funding, 2003 to present, including per-low-income-household measures (per search snippets). | **The resource check's missing third source.** The site returns 403 to scripts, so it needs a manual download. |
| **Legal-deserts work**: [Pruitt et al., *Legal Deserts*](https://journals.law.harvard.edu/lpr/wp-content/uploads/sites/89/2019/04/4.-Legal-Deserts.pdf) (Harvard Law & Policy Review, 2018), the [California Justice Map](https://calatj.squarespace.com/justice-map), [NCSC mapping barriers](https://www.ncsc.org/resources-courts/mapping-barriers-legal-services), [CLASP 2006 state funding per poor person](https://www.clasp.org/sites/default/files/public/resources-and-publications/publication-1/0373.pdf) ($9.55 to $76) | Rural and state-level supply maps: lawyers, offices, drive times. | The supply side, in places, without a debt measure. CLASP's 8× state range (2006) matches the range found in the resource check. |
| **Probative Growth, "Legal-aid, public-interest-law and civil-rights nonprofits by county"** ([Zenodo](https://zenodo.org/records/23782867), v1.0.0, 2026-10-29) | Counts IRS-listed legal-aid nonprofits by mailing-address county. No revenue. The publisher's own note says it is "not a measure of services delivered." | Same IRS source, but a cruder measure than revenue, and it doesn't handle headquarters effects. Not overlapping. |
| **Answer-assistance tools**: Stanford Legal Design Lab's Default Assistant and debt "justice journey" guides; [SoloSuit](https://www.solosuit.com/); [Suffolk LIT Lab](https://suffolklitlab.org/) Court Forms Online | Help people sued for debt respond, or help courts catch bad defaults. | **Relevant to the follow-on education product (PRD open question 5).** Talk to these teams before building it. |

## Gaps this project would fill

- No public map joins a pressure measure (debt in collections, complaints, or lawsuits) to legal aid capacity at sub-state level.
- No published crosswalk turns LSC service areas into county sets with the split counties handled. `docs/phase0/lsc-data/area_county.csv` may be useful to others in its own right.
- No public all-source legal aid revenue by state, apart from LSC's own charts and ABArray. The IRS-based version here checks out against LSC's totals (resource check).

## Not checked

- Google Scholar and SSRN: blocked.
- The APR article's full text and authors: the DOI resolver was blocked by the proxy.
- ABArray's contents: the site returns 403 to scripts.
- Stanford Legal Design Lab and Suffolk LIT Lab project pages: only summaries from search results were seen.
- NCSC beyond one page title, and the Justice Gap 2022 state appendices.

## Implications for the plan

- Phase 0's gap check: no published duplicate found in this scan. The maintainer's Scholar/SSRN search is still needed before calling it.
- Contact LSC's Office of Data Governance and Analysis (CCDI, civilcourtdata@lsc.gov) early, not just at Phase 5. Their court data could replace the one-state lawsuit test, and they may already be building something similar.
- Cite Raval and the APR article in the write-up's caveats on complaints.
- Download ABArray by hand for the resource check's state comparison.
