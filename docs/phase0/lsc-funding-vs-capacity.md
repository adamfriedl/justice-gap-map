# Phase 0: does LSC funding measure legal aid capacity?

_Run 2026-11-06. Fourth Phase 0 check._

## Verdict

- **LSC funding alone fails as a capacity measure.** The federal formula spreads it by poverty population, so it is nearly flat per eligible person ($6.64–$11.79 across states, median $8.56). Total legal aid nonprofit revenue per eligible person runs from $18 to $275 outside DC, and the two barely rank alike (Spearman 0.13). A map built on LSC money would show almost no variation, and what little it showed would be the wrong variation.
- **LSC does publish total revenue from all sources**, nationally and by state (By the Numbers 2025), and per grantee in a public Tableau dashboard. The per-grantee figures aren't downloadable by script.
- **IRS data works as a state-level resource measure.** Revenue for the 121 LSC grantees matched in the IRS Business Master File totals $2.17B. LSC's own figure for total grantee funding is $2.19B. Adding non-LSC legal aid nonprofits roughly doubles the total.
- **Below the state level, 990 data doesn't work as-is.** A statewide organization's revenue sits at its headquarters address. In the median state, the single largest organization holds 49% of legal aid nonprofit revenue.
- **ABA state funding totals: blocked.** `www.americanbar.org` returns 403 to scripts. The site itself refuses, not the proxy. The maintainer would need to download them by hand.

**Resource gate:** passes at the state level. There is a resource measure beyond LSC funding: nonprofit revenue from 990 data, checked against LSC's totals. Below the state level it's open. It depends on how service areas map to counties (the next check). Until then, any sub-state map should say it shows "federal legal aid investment," as the PRD's fallback describes.

## Sources

| Source | Snapshot | Where |
| --- | --- | --- |
| LSC By the Numbers 2025 | PDF on LSC's Box account, downloaded 2026-11-06 | linked from https://www.lsc.gov/our-impact/publications/2025-numbers |
| LSC state profiles | One-page PDF per state and territory, "Funding in 2026" (USVI shows 2025), PDF creation date 2026-06-12, downloaded 2026-11-06 | linked from the public State Profiles page of https://www.lscdataease.org/ |
| LSC grantee list | https://www.lsc.gov/about-lsc/our-grantees, 2026-11-06 (127 grantees) | |
| IRS Exempt Organizations Business Master File | `eo1.csv`–`eo4.csv`, `Last-Modified: 13 Oct 2026`. 1,975,975 organizations. Revenue is from each organization's latest return. | https://www.irs.gov/pub/irs-soi/ |
| ACS 2020–2024 5-year | Population under 125% of poverty, summed from counties to states | Census API (same file as the complaints check) |

Reproduce:

```bash
scripts/phase0_need_download.sh                     # ACS
uv run python scripts/phase0_capacity_fetch.py      # BMF, By the Numbers, grantee list, state profiles
uv run python scripts/phase0_capacity.py --bmf 'data/irs/2026-11-06/eo*.csv' \
    --lsc data/lsc/2026-11-06 --acs data/acs/county_acs5_2024.json --out docs/phase0/capacity
```

Numbers from By the Numbers are quoted from the PDF. Every other number comes from the CSVs in [`capacity/`](capacity/), produced by `scripts/phase0_capacity.py`.

## 1. Does LSC publish total revenue from all sources?

Yes. By the Numbers 2025, Table 2.2, gives total funding for LSC-funded organizations in 2025:

| Source | Amount | Share |
| --- | --- | --- |
| LSC (basic field, other grants, carryover, etc.) | $606.4M | 27.7% |
| State and local grants | $607.5M | 27.8% |
| IOLTA | $260.4M | 11.9% |
| Other federal grants | $237.5M | 10.9% |
| Private grants | $155.0M | 7.1% |
| Other sources, fees | $322.0M | 14.7% |
| **Total** | **$2,188.9M** | 100% |

For Basic Field–General service areas, LSC was 26.3% of $2.13B. The report also gives total funding per eligible person by state (Figures 2.9–2.10, with text), but only as maps and charts. Its text gives a median of $33, with Missouri highest at $91 and Idaho and Alabama lowest at $14. Its denominator is a 2019 ACS special tabulation.

Per grantee: DataEase has a public "Grantee Funding" Tableau dashboard (`public.tableau.com/views/Grantee_Data_Page_Funding/GranteeFunding`). Its `.csv` export redirects to LSC's Tableau profile page instead of returning data. **Not confirmed** whether a person can download the data from the dashboard in a browser. That's worth a manual try, or an email to LSC's data team (datateam@lsc.gov, listed on lsc.gov).

What LSC grantee totals still miss: non-LSC legal aid organizations, which are the rest of the field.

## 2. IRS 990 data (Business Master File) for legal-services nonprofits

**Method.** Take every organization coded NTEE I80 ("legal services"), plus every LSC grantee whatever its code. Grantees are matched to the BMF by normalized name; 11 were matched by hand on a former or legal name, listed in the script. Then set aside four groups:

- LSC itself.
- Criminal defenders: "defender" in the name, plus two named criminal-defense groups.
- Funders and pass-throughs, which would double-count money they regrant to providers: bar foundations, IOLTA programs, state legal services corporations, and access-to-justice foundations.
- I83 ("public interest law"), which is mostly impact litigation. It's kept as a sensitivity figure only.

([bmf_roles.csv](capacity/bmf_roles.csv), [bmf_excluded_1m_plus.csv](capacity/bmf_excluded_1m_plus.csv), [lsc_grantees_bmf_match.csv](capacity/lsc_grantees_bmf_match.csv))

| Group | Orgs | Revenue |
| --- | --- | --- |
| LSC grantees (matched) | 121 | $2,182M |
| Other I80 providers | 1,459 | $2,174M |
| I83 public interest law (sensitivity) | 288 | $697M |
| Set aside: defenders | 66 | $534M |
| Set aside: funders and pass-throughs | 49 | $448M |
| Set aside: LSC itself | 1 | $573M |

**Validation.** Matched grantee revenue in the BMF, $2.17B for states with a profile, lands within 1% of LSC's $2.19B. The two don't measure exactly the same thing: fiscal years differ, LSC's figure excludes client-service income, and 6 grantees didn't match. Still, the BMF is clearly measuring the same money.

**By state** ([state_capacity.csv](capacity/state_capacity.csv), [capacity_summary.csv](capacity/capacity_summary.csv)). All figures are per person under 125% of poverty.

| | Min | 10th pct | Median | 90th pct | Max |
| --- | --- | --- | --- | --- | --- |
| LSC funding, 2026 (51 states) | $6.64 | $7.84 | $8.56 | $9.00 | $11.79 |
| LSC grantees' total revenue | $8.89 | $14.73 | $28.84 | $56.23 | $173.67 |
| All legal aid providers (grantees + other I80) | $17.72 | $26.21 | $52.20 | $159.43 | $1,623 (DC) |

- Spearman, LSC per eligible vs. all providers per eligible: **0.13** (51 states).
- Provider revenue runs 2.4x LSC funding in Alabama and 30.9x in New York (median 6.3x).
- Rank shifts are large. Vermont has the 3rd-lowest LSC funding per eligible person and the 48th-highest total. Maine goes from 6th-lowest to 46th, Nebraska from 4th to 41st. Idaho is last on both.
- The bottom of the provider table is the South and Mountain West: Idaho, Alabama, Mississippi ($20–21), then Nevada, South Carolina, Kentucky, Georgia ($26–27). The top is DC, New York, Colorado, Vermont, New Jersey, and Maine. This is descriptive only; it says nothing about how well any program performs.

**Problems with the 990 approach.** Each one affects how the data can be used:

- **Location is the headquarters.** DC's $1,623 reflects national organizations based there (KIND, Namati). Texas RioGrande Legal Aid's revenue all lands in Texas, though it also serves farmworkers in six other states. Pine Tree Legal Assistance (Maine) runs the New England farmworker grant.
- **Statewide organizations dominate.** The largest single organization holds a median 48.8% of a state's provider revenue, and at least half in 24 of 51 states. Placing that revenue at a headquarters county would make the capital, or wherever the HQ sits, look rich and the rest of the state look empty.
- **NTEE coding is inconsistent.** Some LSC grantees are coded I83 (e.g. Northwest Justice Project) or have no code at all. Large non-grantee providers can be miscoded the same way.
- **The set-aside rules are name-based and rough.** A few large I80 organizations are hard to classify from a name alone, such as Community Firm (CO, $102M) and Purpose Dignity Action (WA, $37M). Both stay in the provider total. The state ranking barely moves when funders are added or removed, but individual state figures could shift by several dollars per person.
- **6 grantees didn't match**, so their revenue is missing: Community Legal Services of Mid-Florida, Kentucky Legal Aid, Legal Aid Society of Greater Cincinnati, Legal Services of Eastern Missouri, Legal Services of Northwest Jersey, and Legal Services of Southern Missouri. Florida, Kentucky, Ohio, New Jersey, and Missouri are undercounted.
- **Arkansas's profile PDF has no dollar figure**, so Arkansas has no LSC-per-eligible value.
- LSC funding per eligible person here uses ACS 5-year counts. LSC allocates using Census special tabulations, which is why it isn't perfectly flat.
- Revenue isn't capacity. Staff, attorneys, and caseload would be closer. By the Numbers and GAR report those, but by grantee, not for the rest of the field.

**Decision on statewide organizations:** use 990 revenue at the state level only. Below the state level, either spread a statewide organization's revenue across its service area in proportion to eligible population (an assumption, stated as one), or leave non-LSC capacity off the sub-state map and say so. Don't place revenue at the HQ county.

## 3. State civil legal aid funding totals (ABA)

Not done. `https://www.americanbar.org/` returns HTTP 403 to scripts. The proxy allowed the connection; the site itself refused. Per AGENTS.md, I didn't route around it. If the maintainer downloads the ABA Resource Center for Access to Justice Initiatives' state funding survey by hand, it can serve as a third check on the state ranking above. By the Numbers' state-and-local line ($607.5M for LSC grantees) partly covers the same ground.

## Implications for the plan

- Drop "LSC basic field funding per eligible resident" as the resource measure. By construction it's nearly constant.
- State level: use total legal aid nonprofit revenue per eligible person from 990 data, alongside LSC grantees' all-source revenue from By the Numbers or DataEase if the per-grantee data can be had.
- Sub-state level: depends on the LSC data-availability check (service areas as county sets). Without it, the title should say "federal legal aid investment," or the map should show pressure only, per the PRD.
- `pypdf` is added to read LSC's PDFs.
- Hosts this check used, added to the environment this session: `lsc-live.app.box.com`, `lsc-live.box.com`, `app.box.com`, `public.boxcloud.com`, `dl.boxcloud.com` (LSC's files), and `public.tableau.com` (DataEase dashboards). ProPublica's 990 XML download (`projects.propublica.org/nonprofits/download-xml`) returned 403 from the site, so LSC's Schedule I grant list wasn't used.
