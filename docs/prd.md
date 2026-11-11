# Justice Gap Map: PRD and plan

_Drafted 2026-11-05; revised 2026-11-07 after the Phase 0 data checks, and again on 2026-11-07 to make v1 a debt-lawsuit monitor. Working name. Gated on the Phase 0 go/no-go: the data checks pass; the maintainer's literature search and the one-state prototype remain._

## Summary

A small, repeatable data pipeline on AWS that joins public datasets:

- The Urban Institute's county share of people with debt in collections (the pressure measure)
- CFPB debt-collection complaints (a secondary signal: where people push back)
- Legal Services Corporation (LSC) service areas and awards, plus IRS data on all legal aid nonprofits' revenue
- Census ACS demographics

**v1 is a debt-lawsuit monitor.** It watches where debt-collection suits are filed, who files them, and how they end, refreshing each source on its own schedule (daily to yearly). It keeps its own history and sends an alert when something moves. Lawsuit data is state by state, so coverage grows one state or county at a time. Debt in collections and CFPB complaints are national context.

It answers one question: **where are people taking the most consumer-debt harm while having the least civil legal aid?** The outputs are a published map, a short write-up, and an optional plain-English query layer in the style of [civicaitools.org](https://civicaitools.org/).

The longer-term goal is legal-process education for people who default on a complaint out of fear, or who show up and get bulldozed because they don't know the process. This map shows where that help is needed most.

## Problem

- Debt collection cases end in default more than 70% of the time (Pew, 2020). Many defendants had a defense or could have negotiated.
- People often don't recognize these problems as legal (Sandefur, ABF), so they never look for help.
- Civil legal aid is scarce and unevenly funded. LSC's Justice Gap studies document the unmet need nationally, but it's hard to see at a local level.
- Each piece is public, but the datasets don't line up. CFPB uses ZIP codes, LSC uses service areas, and ACS uses tracts and counties. Nobody has put them in one place. (A preliminary scan on 2026-11-07 found no published combination; LSC's Civil Court Data Initiative is the closest effort. See `docs/phase0/literature-scan.md`. Scholar and SSRN not yet searched.)

## Audience

| Who | What they get |
| --- | --- |
| Legal aid program and development staff | Evidence for grant applications and for deciding where to do outreach |
| A2J researchers and funders (LSC, state IOLTA, legal design labs) | A reproducible local view of need vs. resources |
| Civic tech and open-data people | A worked example of joining mismatched federal datasets |

## Goals

0. **A working monitor.** Scheduled pulls keep county debt-filing counts current (monthly where courts publish monthly), and case-level feeds current within a day for the counties that offer them. A weekly alert flags unusual changes by county or plaintiff.
1. **One defensible finding.** For example: "These N service areas have the highest debt-collection complaint rate per eligible resident and the lowest LSC funding per eligible resident." It must hold up to a legal-aid reader's scrutiny.
2. **Reproducible and refreshable.** One command (or a schedule) pulls new data, rebuilds the tables, and regenerates the map. No manual steps.
3. **An independent archive.** Keep dated, unchangeable snapshots of the CFPB data. The CFPB has been politically exposed since 2025, and an archive matters if the public data is restricted.
4. **All infrastructure in Terraform on AWS**, written to be read: the maintainer reviews every infra PR and can explain it in 10 minutes.
5. **Cheap.** Idle cost near $0, and under ~$10/month while active.

## Non-goals (v1)

- A national lawsuit measure. Court data comes state by state (Texas, Indiana and Virginia so far; see `docs/lawsuits/`). Coverage grows as states are added, and maps say which states are covered.
- Storing names or street addresses of people sued (R15).
- Products other than debt collection. The pipeline should handle any product, but only debt collection gets analyzed.
- Causal claims. This is descriptive: it shows where need and resources diverge, not why.
- Calling out, ranking, or criticizing legal aid providers, LSC, or other legal aid funders. See "Purely informational" below.
- A polished web app. A static map plus a write-up is enough.
- The education product itself. This project picks where it should go first.

## Purely informational

About the legal aid side, everything published here reports what public records show. It doesn't judge legal aid providers, LSC, or other legal aid funders (IOLTA programs, bar foundations, and the like).

- **Name places, not programs.** Maps, headlines, and rankings are about counties, service areas, and states. Grantee and nonprofit names appear only as source columns in data tables, never in map labels, headlines, or ranked lists.
- **Funding describes money reaching an area, not how a program performs.** Say "federal legal aid investment per eligible resident in this area," never "this program is underfunded" or "under-serving."
- **Plaintiffs are fair game.** Debt buyers, collectors, lenders, and their law firms can be named, ranked, and described: who files the most, how fast filings grow, how often their cases end in default. Every claim about a named plaintiff comes from court records and links to its source and script.
- **Neutral words about places and legal aid.** Use "higher," "lower," "more," "fewer." Avoid "worst," "failing," "neglected," and the like. For plaintiffs, let the numbers make the point ("filed 12,000 suits; 80% ended in default") rather than labels such as "predatory": facts from court records hold up, labels invite argument.
- **Frame gaps as where more help could go,** not as who is at fault.

## Data sources

| Source | What | Geography | Refresh | Known issues |
| --- | --- | --- | --- | --- |
| [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/) | Every published complaint: product, issue, company, date, state, ZIP, company response, optional narrative | 5-digit ZIP, 3-digit ZIP, or blank | Daily | ZIP is shortened or hidden for small-population areas, and the rules differ between docs ([field reference](https://cfpb.github.io/api/ccdb/fields.html), [data-use page](https://www.consumerfinance.gov/complaint/data-use/)). Only people who know about the CFPB file, so expect awareness bias. The data may not continue. |
| [LSC service areas](https://www.lsc.gov/grants/basic-field-grant/lsc-service-areas) (public JSON behind lsc.gov's map), [state profiles and DataEase](https://www.lscdataease.org/), [By the Numbers](https://www.lsc.gov/our-impact/publications/2025-numbers) | Service-area county definitions, current grantee, latest LSC award, eligible population; state LSC funding; national and state all-source funding and case closures | 130 general service areas, built as county sets (122 analysis units after merging areas that share a split county); state | Annual (areas re-competed on a 3-year cycle) | No downloadable boundary file used. Case closures are state-level only. All-source funding per grantee is a Tableau view only. |
| Census ACS 5-year (API) | Population at or below 125% of poverty (LSC's eligibility line), renters, limited English, broadband, age | Tract, county, ZCTA | Annual | Margins of error get large in small areas |
| [Urban Institute, Debt in America](https://apps.urban.org/features/debt-interactive-map/) | Share of people with a credit record who have any debt in collections (4% panel from one bureau) | County (3,071 of 3,143 with values) | Irregular (current: August 2025 data, published 2025-11-20) | Measures who is being collected on, whether or not they complain. Excludes people without credit records. Connecticut uses pre-2022 counties. CSVs pulled from the map's own data path. |
| [IRS Exempt Organizations Business Master File](https://www.irs.gov/pub/irs-soi/) | Revenue of legal aid nonprofits (NTEE I80, plus LSC grantees), LSC-funded or not | Organization headquarters | Monthly | An address isn't a service area: use at state level, or spread a statewide organization over its area. Funders and defenders must be set aside. |
| Texas Office of Court Administration ([card.txcourts.gov](https://card.txcourts.gov/)) | Justice-court debt-claim filings, defaults, dispositions | County (254) | Monthly | Report form, not an API: one request per county per period. Some counties report late or not at all (Hidalgo). |
| [Harris County JP Public Data Extract](https://jpwebsite.harriscountytx.gov/PublicExtracts/search.jsp) | Each debt-claim case: plaintiff and attorney, filing date, claim amount, next hearing, disposition, judgment | Case; defendant ZIP | Daily | Contains defendants' names and addresses: stripped in memory before storage (R15). Up to 180 days per request. |
| [Indiana Court Online Reports](https://publicaccess.courts.in.gov/ICOR/) | Collection (CC) filings, defaults, dispositions | County (92) | Quarterly | Small claims also hold debt suits, not separated. |
| [Virginia General District Court filing report](https://www.courts.state.va.us/static/courtadmin/aoc/djs/programs/cpss/csi/stats/gdc_filings.pdf) | General Civil filings (mostly warrants in debt) and garnishments | Court (125) | Monthly | PDF; category broader than debt (**not confirmed** share). |
| [HUD-USPS ZIP crosswalk](https://www.huduser.gov/portal/datasets/usps_crosswalk.html) | Weights for converting ZIP ↔ county/tract | ZIP → county | Quarterly | Use the file that goes in the right direction. Some ZIPs are missing. Needs a registered API token. |

**Unit of analysis:** 122 analysis units built from LSC's 130 Basic Field–General service areas as county sets, merging the areas that share a split county (`docs/phase0/lsc-data/`). County is the building block. State is used where only state data exists (all-source revenue, case closures).

**Core metrics.** "Eligible" means the ACS population under 125% of poverty.

- **Pressure (primary):** share of people with debt in collections (Urban), population-weighted from counties to units.
- **Pressure (secondary):** debt-collection complaints per 10K residents, counted once per ZIP and day to blunt batch filing.
- **Collections without complaints:** units with high debt in collections but few complaints, where people may not be pushing back (open question 4). Report it as its own layer, not folded into the gap score.
- **Resources (unit level):** LSC award per eligible resident. Label it "federal legal aid investment," because by formula it is nearly flat per eligible person.
- **Resources (state level):** total legal aid nonprofit revenue per eligible resident (IRS data, checked against LSC's own totals). It varies about 8× across states, so show it as state context. A unit-level version needs a stated allocation assumption for statewide organizations.
- **Gap score:** rank of pressure minus rank of resources, within the same scope (units within a state for LSC awards, states for total revenue). Explained in plain words, not a black box.
- **Context columns:** share of renters, share with limited English, share without broadband, and the share of complaints that couldn't be placed in a county (ZIP masking).

Why these changed (Phase 0, `docs/phase0/`):

- Complaints don't track lawsuits in Texas, and the poorest counties complain least. Complaints also rise where legal aid offices exist (literature scan).
- LSC funding per eligible person is nearly constant by formula, and ranks states unlike total funding (Spearman 0.13).

## Requirements

### Pipeline

- R1. Download each source into a raw S3 bucket under dated keys, unchanged (except case-level court data, reduced under R15 before it is written). The raw bucket is versioned, with Object Lock (governance mode, 365 days) on every object; the first draft limited the lock to the CFPB prefix.
- R2. Normalize to Parquet in a curated bucket, partitioned by source and snapshot date.
- R3. Write geography crosswalks (ZIP → county → service area) once per snapshot and version them.
- R4. Build the metric tables with SQL (Athena, with DuckDB for local development). Keep queries in the repo.
- R5. Every published number traces back to the snapshot dates and query that produced it.
- R15. **No personal identifiers for people sued.** Case-level court feeds are reduced in memory before anything is stored: defendant names, street addresses, the case style, and "judgment against" fields are dropped; only defendant ZIP and whether they had an attorney are kept. Plaintiffs (businesses) and their attorneys are kept. Tests enforce this.
- R16. **Alerts.** A weekly job compares each county's and each top plaintiff's filings with their own recent baseline and emails a short summary (SNS) when something moves well outside it. Thresholds live in the repo.
- R17. **Polite collection.** Each court source has a documented request rate and pause, honors its terms and robots.txt, and backs off on errors. No source is hit more often than it updates.
- R6. Report data quality on every run: how many complaints were dropped for missing or 3-digit ZIPs, broken down by state, and how many ZIPs the crosswalk couldn't match.

### Outputs

- R7. A static choropleth map with a sortable table, published on GitHub Pages.
- R8. A write-up (~1,500 words): the question, the method, the finding, the caveats, and what a legal aid program could do with it.
- R9. Optional: a read-only query layer, either an MCP server over the curated tables or a small notebook. It shows the SQL it ran.

### Infrastructure

- R10. All of it in Terraform: S3 (raw and curated), Glue catalog, an Athena workgroup with a scan limit, IAM roles, an EventBridge Scheduler schedule plus the job runner, Parameter Store, a budget alarm.
- R11. GitHub Actions authenticating through OIDC. `terraform plan` on PRs; `apply` on merge to main, in a `production` GitHub environment limited to `main` (the maintainer's merge, after reading the plan, is the gate; required reviewers on the environment are available but not used).
- R12. Least privilege: the ingest role writes only to raw, the transform role reads raw and writes curated, the query role is read-only on curated.
- R13. Scales to zero when idle. No always-on compute.
- R14. **Read-only cloud-session access.** An IAM user `claude-cloud-readonly`, defined in Terraform, whose access key lives only in the Claude Code cloud environment's env vars. It may:
  - read the raw and curated buckets (`s3:GetObject`, `s3:ListBucket`)
  - run Athena queries in the project workgroup only, writing results only to an `athena-scratch/` prefix (the one write it has), and read the Glue catalog
  - read the project's CloudWatch logs and ECS/Lambda job status

  It has no IAM, no resource creation or deletion, no access to other buckets, and no writes to raw or curated. A permissions boundary caps it even if its policy is later loosened by mistake. Keys are rotated at least every 90 days and on any suspicion. Its access must be visible in CloudTrail.

## Architecture (v1)

```text
EventBridge Scheduler: daily Harris County cases; weekly CFPB; monthly Texas OCA
and Virginia courts; quarterly Indiana courts and HUD; annual ACS, Urban, IRS, LSC
        │
        ▼
Ingest job (Lambda for small pulls; ECS Fargate task for the ~GB CFPB zip)
        │  writes dated, untouched files
        ▼
S3 raw  (versioned; Object Lock on cfpb/)
        │
        ▼
Transform job (Fargate, Python + DuckDB) ── crosswalks, Parquet, DQ report
        │
        ▼
S3 curated (Parquet) ── Glue catalog ── Athena workgroup (scan cap)
        │
        ├── metrics export → static map site (GitHub Pages)
        ├── weekly alert job → SNS email (R16)
        └── optional: read-only MCP server / notebook
```

Why AWS: the case-level feeds grow by roughly 100K+ debt cases a year for Harris County alone (OCA counted 91,823 in 2025; the first extract week, October 1–7, 2026, held 2,863), and need daily scheduling, a locked archive, and a query surface; county counts update monthly. Design choice: DuckDB inside the Fargate task does the heavy transforms (cheap and testable locally), and Athena is the shared query surface. Glue crawlers are skipped. Table definitions live in Terraform.

## Plan

Each phase ends with something you can show. Estimates assume part-time evenings.

### Phase 0: data spikes and gap check (3–4 evenings, before any infra)

This decides whether the project is viable. No AWS needed, so it suits cloud sessions. Raw downloads stay out of git. Commit only small results (tables, notes) under `docs/phase0/`.

- [x] **LSC:** find out exactly what's downloadable: service area boundaries or their county lists, funding by grantee or service area, and GAR case closures. If service areas can't be rebuilt from counties, switch the unit to county and write the reason down.
  _Done 2026-11-07: all 130 general service areas parse into county sets covering every county; 13 split a county (11.5% of eligible people), so merging those gives 122 analysis units with each county in exactly one. FY2025 LSC awards by area come from the same source. GAR closures by state only. See `docs/phase0/lsc-data-availability.md`._
- [x] **CFPB:** download the full CSV. Measure the share of debt-collection complaints with a 5-digit ZIP, a 3-digit ZIP, or none, by state. If more than ~30% can't be placed, reconsider the unit (state, or 3-digit ZIP areas).
- [x] **Crosswalk:** pull HUD ZIP→county and check how many complaint ZIPs it matches.
  _Both done 2026-11-06: 89.5% of debt-collection complaints place in a county, but masking hits rural states hardest. See `docs/phase0/cfpb-zip-and-crosswalk.md`._
- [x] **Do complaints measure need?** Most debt cases end in default, and people who default are the least likely to file a CFPB complaint, so complaint rates may run opposite to need.
  - Get a pressure measure that doesn't depend on awareness: confirm the Urban Institute's county-level debt-in-collections data is downloadable and how recent it is.
  - In one state with open court data (January Advisors' Texas work first), compare county complaint rates with county debt-lawsuit filing rates, and with debt in collections.
  - Explain the 2024–26 jump in debt-collection complaints (68K in 2023, 283K in 2025). Compare 2021 and 2025 by submission channel, issue mix, and company concentration. If bulk third-party filings drive it, filter them or use a pre-2024 baseline.
  _Done 2026-11-06: complaints fail (in Texas they barely track debt lawsuits, and the poorest counties complain least); Urban's county debt-in-collections share is usable and becomes the pressure measure. See `docs/phase0/complaints-vs-need.md`._
- [x] **Does LSC funding measure capacity?** LSC is a minority of civil legal aid funding, and state, IOLTA, and private money varies a lot by state. LSC-only figures would make states that fund legal aid heavily look underserved.
  - Check whether LSC publishes grantees' total revenue from all sources, not just their LSC grant.
  - Test IRS 990 data for legal-services nonprofits (NTEE I80-range) as a way to include non-LSC organizations. Decide how to handle statewide organizations.
  - Pull state-level civil legal aid funding totals (e.g. the ABA's access-to-justice resource center) as a check on the state skew.
  _Done 2026-11-06: LSC funding is nearly flat per eligible person by formula and fails as a capacity measure; 990 nonprofit revenue works at the state level (matches LSC's grantee totals within 1%) but not below it; ABA totals blocked (site returns 403). See `docs/phase0/lsc-funding-vs-capacity.md`._
- [ ] **Gap check, done properly:** search Google Scholar and SSRN. Check LSC's own reports, the NCSC, Pew, January Advisors (debt lawsuit data), and the Stanford Legal Design Lab and Suffolk LIT Lab sites. If someone already did this, look for what they left out or contribute to their work instead.
  _Preliminary scan done 2026-11-07 (no Scholar/SSRN): no published combination found; LSC's Civil Court Data Initiative is the nearest effort and a likely partner. See `docs/phase0/literature-scan.md`. The maintainer still searches Scholar and SSRN._
- [ ] **One hand-built prototype:** a single state (pick one with clean ZIPs and county-based service areas) in DuckDB. Does any signal show up? Texas is the natural pick: court filings are already pulled, its three general service areas (TX-13, TX-14, TX-15, one grantee each) are whole-county lists, so no merged units are needed. Use the revised metrics above.
  _Started 2026-11-08 with legal aid offices: 81% of Texas debt suits are filed in the 43 counties with an office, so distance isn't where the gap shows; suits per eligible resident range from 81 to 120 per 1,000 across the three service areas, each with 14–16 offices. See `docs/legal-aid/texas.md`._

**Go/no-go:** continue if LSC data can be attached to some geography, more than ~70% of complaints can be placed, and nobody has already published this. Also:

- **Pressure:** there's a pressure measure that holds up. Either complaints track lawsuit filings in the test state, or an awareness-free measure (debt in collections) is usable. If neither, stop: the map would point help at the wrong places.
- **Resources:** there's a resource measure beyond LSC funding. If there isn't, narrow the claim to "federal legal aid investment vs. need" and say so in the title, or map pressure alone.

Otherwise write down why in `docs/phase0/` and stop.

**Decision (2026-11-07): go.** The maintainer chose to proceed to Phase 1, with v1 as a debt-lawsuit monitor.

**Status (2026-11-07):**

| Condition | Status | Evidence |
| --- | --- | --- |
| LSC data attaches to a geography | **Pass** | 122 county-set units; awards per area |
| >~70% of complaints placeable | **Pass** | 89.5% county-placeable |
| Pressure measure holds up | **Pass, on debt in collections** | Complaints fail in Texas |
| Resource measure beyond LSC | **Pass at state level; open below it** | IRS revenue matches LSC's totals within 1%; unit-level needs an allocation assumption |
| Nobody has published this | **Preliminary pass** | Literature scan; Scholar/SSRN pending |

### Phase 1: AWS bootstrap (run once locally with admin credentials)

- [x] Account hygiene, S3 Terraform state backend with `use_lockfile`, GitHub OIDC provider and plan/apply roles scoped to this repo
  _Applied 2026-11-08 (us-east-2, because of the account's organization region rule), with the trust policies updated the same day for GitHub's immutable OIDC subject format. Written in `infra/bootstrap/` with a runbook in `docs/aws-setup.md`; the maintainer applies it by hand. The bootstrap runs as a plain IAM admin user (no IAM Identity Center), a machine user whose access key exists only for the bootstrap and is deleted afterwards._
- [x] A GitHub `production` environment limited to `main`; `apply` runs on merge
  _Verified 2026-11-08: `plan` ran on a PR through OIDC, and the first apply-on-merge ran on `main`._
- [x] The permissions boundary for `claude-cloud-readonly` (R14). The user itself was later moved into the bootstrap too, with that policy as both its boundary and its only policy, so CI can't widen it.

Cloud sessions never get write access to AWS. Every change reaches AWS through Actions. After Phase 2 they can hold the read-only key from R14 for querying and debugging.

### Phase 2: pipeline infrastructure (~6–8 hours)

- [ ] Terraform under `infra/` _(storage and catalog done 2026-11-09; the first job, its schedule and its ingest role drafted 2026-11-11 in `infra/main/jobs.tf`: a daily Lambda for Harris County. Still to do: the other ingest jobs, the Fargate transform, the transform and query roles. Plain files in one stack so far, not modules.)_: `storage` (raw/curated buckets, versioning, Object Lock, lifecycle), `catalog` (Glue database and tables, Athena workgroup with a 1 GB scan cap), `jobs` (ECR repo, Fargate task definitions, Lambda), `schedule` (EventBridge Scheduler), `iam` (the three roles from R12, plus the `claude-cloud-readonly` user from R14), `budget`
- [ ] After apply, the maintainer creates the read-only user's access key in the console and pastes it into the cloud environment's env vars (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`). Terraform must not create the key, so it never lands in state.
- [x] Threat model, one page, written **before** building: data integrity of the archive, IAM blast radius, and the public site (STRIDE)
  _Done 2026-11-09: `docs/threat-model.md`._
- [ ] CI: plan on PRs, apply on main, tflint + checkov

### Phase 3: ingest + transform (~8–10 hours)

- [ ] Ingest jobs for CFPB, ACS, the HUD crosswalk, Urban debt in collections, the IRS BMF, and LSC (`about.json` per service area plus state profiles; scriptable, no manual drop needed)
- [ ] Court ingest jobs _(Harris County drafted 2026-11-11: `src/ingest_harris.py`, each run a snapshot of cases filed in the last 30 days)_: Harris County cases (daily, R15 applied in the job), Texas OCA counties (monthly), Virginia filing report (monthly), Indiana ICOR (quarterly). The fetch scripts in `scripts/lawsuits_fetch_*.py` and `scripts/phase0_tx_courts_fetch.py` are the starting point.
- [ ] Plaintiff name normalization (case, punctuation, "successor by merger" variants) as a versioned lookup table.
- [ ] Transform job: CSV → Parquet, apply the crosswalk, write the DQ report (R6)
- [ ] Local dev path: the same Python running against local files with DuckDB, plus a small fixture dataset for tests
- [ ] Turn on the schedule. Confirm a weekly CFPB snapshot lands and is locked.

### Phase 4: analysis + outputs (~6–8 hours)

- [ ] Metric SQL (R4) and gap score
- [ ] Sanity checks: does the national total match published CFPB counts? Does total LSC funding match published totals? Do the top-ranked areas make sense to someone who knows the region?
- [ ] Static map + table (R7)
- [ ] Draft the write-up (R8)

### Phase 5: publish

The repo is public from 2026-11-08, so the work is visible as it happens. Everything in it follows "Purely informational" above.

- [ ] Accuracy check before the map and write-up go on GitHub Pages: ask 1–3 people who know the field (LSC's data office, a legal aid program, a court data researcher) whether the data is read correctly and what would make it useful. This checks accuracy. It doesn't give anyone a veto.
- [ ] Publish the map and write-up (R7, R8).

### Phase 6: optional extras

- [ ] Read-only query layer (R9): MCP server over Athena, showing the SQL it ran
- [ ] Add a second CFPB product (credit reporting, mortgages)
- [ ] v2: court-side data for more states with open debt-lawsuit records, building on the Phase 0 test state

**Total to a published v1:** roughly 30–40 hours after Phase 0.

## Success criteria

- Phase 0 go/no-go was decided on evidence and written down
- A scheduled run refreshes everything with no manual steps (LSC excepted, if it's a documented manual drop)
- At least 3 months of locked CFPB snapshots exist
- A map and write-up are published, and at least one legal aid or A2J reader has reviewed them and called them useful or correct
- The maintainer can walk through the architecture, IAM, and the data caveats in 10 minutes

## Risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| LSC data is too coarse or not downloadable | Low (was medium-high) | Resolved in Phase 0: service areas as county sets, with awards. Pull `about.json` yearly; it depends on an undocumented public endpoint. |
| CFPB ZIP masking hides too much in rural areas | Medium | Measure in Phase 0; report it openly; use 3-digit ZIP areas or state for affected regions |
| CFPB data restricted or discontinued | Medium | Archive from week one. If it happens, the archive becomes the story. |
| Complaints track awareness, not need: people who default rarely complain | Confirmed | Switched: debt in collections is the pressure measure; complaints are secondary |
| LSC funding misses most legal aid capacity, skewing results by state | Confirmed | Unit maps say "federal legal aid investment"; state context uses total nonprofit revenue |
| Urban's debt data stops or changes method | Medium | Updates are irregular, and its medical-debt reporting already shifted. Pin the vintage; keep complaints as a fallback layer. |
| LSC builds the same thing (its Civil Court Data Initiative) | Medium | Contact LSC's data office early; aim to complement or contribute rather than duplicate |
| The finding just matches "poor places have less help" | Medium | Still useful locally. Look for surprises (well-funded areas with high complaint rates, and the reverse). Say so plainly if nothing surprising shows up. |
| Scope creep into a web app | High | Static site only until v1 is published |
| Court sites change layout or block automated access | Medium | Each fetcher checks expected columns and fails loudly (the Harris fetcher does); polite rates (R17); monthly sources tolerate a missed run |
| Personal data about people sued leaks or is retained | Low with R15 | Strip in memory before storage; tests; no defendant fields in the curated schema; threat model covers it |
| The finding reads as an attack on LSC, grantees, or other legal aid funders | Low-medium | "Purely informational" rules (places, not programs; neutral words); Phase 5 accuracy check; frame it as "where more help could go," not "who is failing" |

## Open questions

1. ~~What unit of analysis can the LSC data actually support?~~ Answered: 122 county-set units (Phase 0).
2. Is a 3-year complaint window right, or should it be by year to show trends? Decide after seeing the data.
3. ~~Is there a state with open debt-collection court data good enough for the Phase 0 validity test?~~ Answered: Texas OCA justice-court data. LSC's Baseline Court Statistics has explicit debt case types for 7 more states.
4. Is the gap between debt in collections and complaints the real finding? (Now a planned layer; see core metrics.) Counties with lots of debt in collections but few complaints are where people aren't fighting back, which is where defaults happen.
5. Is the education product the follow-on, with this map picking where to start? The Harris County feed includes next hearing dates by court, which shows where and when people sued for debt are about to appear. The idea: a 30-second "what happens next" walkthrough reachable from the summons, for one case type in one jurisdiction.
6. How should a statewide organization's revenue be spread over its service area? By eligible population, or not at all below state level?
