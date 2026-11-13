# Debt Docket: PRD and plan

_Drafted 2026-11-05 as "Justice Gap Map"; revised 2026-11-07 after the Phase 0 data checks, and again on 2026-11-07 to make v1 a debt-lawsuit monitor. Reframed 2026-11-13 around the Harris County docket: the county map was retired, and the legal aid comparison became earlier work. Repository and AWS resource names stay `justice-gap-map`._

## Summary

A small, repeatable data pipeline on AWS that reads case-level court records for debt-collection lawsuits and reports **who files them, for how much, and how they end.** It starts with Harris County, Texas (Houston), whose justice courts publish a daily case extract, and adds places one at a time as courts publish usable records.

It keeps its own dated history of each feed, rebuilds the tables on a schedule, and sends an alert when a large plaintiff's filings move sharply. Statewide counts (Texas, Indiana, Virginia) give context: how big one county is against its state, and where to look next.

The outputs are a published docket page, a short write-up, and an optional plain-English query layer in the style of [civicaitools.org](https://civicaitools.org/).

The longer-term goal is legal-process education for people who default on a suit out of fear, or who show up and get bulldozed because they don't know the process. The docket shows where and when people sued are due in court, which is where that help would start.

### How it got here

The first framing asked where consumer-debt harm is high and civil legal aid is thin, joining CFPB complaints, Urban's debt-in-collections data, LSC service areas and Census data. Phase 0 found that complaints don't track need and LSC funding doesn't measure capacity (`docs/phase0/`). The county map that followed couldn't compare states and divided by the wrong year's population. The Harris County docket, counted straight from court records with no proxies or denominators, held up better, so it became the project. The sections below that describe the earlier framing (core metrics, Phase 0) are kept as a record.

## Problem

- Debt collection cases end in default more than 70% of the time (Pew, 2020). Many defendants had a defense or could have negotiated.
- People often don't recognize these problems as legal (Sandefur, ABF), so they never look for help.
- The records that show who sues, for how much, and how cases end are public in some courts, but scattered, in formats built for looking up one case, and rarely summarized. Statewide reports count cases without saying who filed them.

## Audience

| Who | What they get |
| --- | --- |
| Legal aid programs, court staff, and consumer advocates | Who files debt suits locally, how large the claims are, and how cases end, from the court's own records |
| Researchers and journalists | Reproducible tables with the query behind every figure |
| Civic tech and open-data people | A worked example of a small, reviewable pipeline over a public court feed |

## Goals

0. **A working monitor.** Case-level feeds stay current within a day for the places that offer them. A weekly alert flags a large plaintiff whose filings move well outside its own recent weeks (R16).
1. **One defensible docket.** Who files, for how much, and how cases end, for one place, holding up to a reader who knows the court. Every figure comes from court records and names its source and query.
2. **Reproducible and refreshable.** A schedule pulls new data and rebuilds the tables and page. No manual steps.
3. **An independent archive.** Keep dated, unchangeable snapshots of each feed. Court sites change and public data can be restricted.
4. **All infrastructure in Terraform on AWS**, written to be read: the maintainer reviews every infra PR and can explain it in 10 minutes.
5. **Cheap.** Idle cost near $0, and under ~$10/month while active.

## Non-goals (v1)

- A national lawsuit measure or a national map. Court data comes place by place, and states define debt cases differently.
- Rates per resident or comparisons across states. The docket counts cases; statewide counts are context.
- Storing names or street addresses of people sued (R15).
- Case types other than debt collection.
- Causal claims. The docket describes what the records show, not why (for example, what an attorney changes).
- Calling out, ranking, or criticizing legal aid providers, LSC, or other legal aid funders. See "Purely informational" below.
- A polished web app. A static page plus a write-up is enough.
- The education product itself.

## Purely informational

About the legal aid side, everything published here reports what public records show. It doesn't judge legal aid providers, LSC, or other legal aid funders (IOLTA programs, bar foundations, and the like).

- **Name places, not programs.** Headlines, charts, and rankings are about places and plaintiffs. Legal aid organizations are never named in headlines, chart labels, or ranked lists.
- **Plaintiffs are fair game.** Debt buyers, collectors, lenders, and their law firms can be named, ranked, and described: who files the most, how fast filings grow, how often their cases end in default. Every claim about a named plaintiff comes from court records and links to its source and script.
- **Neutral words about places and legal aid.** Use "higher," "lower," "more," "fewer." Avoid "worst," "failing," "neglected," and the like. For plaintiffs, let the numbers make the point ("filed 12,000 suits; 80% ended in default") rather than labels such as "predatory": facts from court records hold up, labels invite argument.

## Data sources

The Harris County extract is the docket; the state counts are context. The sources used only by the earlier map (CFPB complaints, Census ACS, Urban's debt in collections, LSC service areas, IRS nonprofit revenue, the HUD ZIP crosswalk) are dropped from the plan; what Phase 0 found with them is in `docs/phase0/`.

| Source | What | Geography | Refresh | Known issues |
| --- | --- | --- | --- | --- |
| Texas Office of Court Administration ([card.txcourts.gov](https://card.txcourts.gov/)) | Justice-court debt-claim filings, defaults, dispositions | County (254) | Monthly | Report form, not an API: one request per county per period. Some counties report late or not at all (Hidalgo). |
| [Harris County JP Public Data Extract](https://jpwebsite.harriscountytx.gov/PublicExtracts/search.jsp) | Each debt-claim case: plaintiff and attorney, filing date, claim amount, next hearing, disposition, judgment | Case; defendant ZIP | Daily | Contains defendants' names and addresses: stripped in memory before storage (R15). Up to 180 days per request. |
| [Indiana Court Online Reports](https://publicaccess.courts.in.gov/ICOR/) | Collection (CC) filings, defaults, dispositions | County (92) | Quarterly | Small claims also hold debt suits, not separated. |
| [Virginia General District Court filing report](https://www.courts.state.va.us/static/courtadmin/aoc/djs/programs/cpss/csi/stats/gdc_filings.pdf) | General Civil filings (mostly warrants in debt) and garnishments | Court (125) | Monthly | PDF; category broader than debt (**not confirmed** share). |

**Unit of analysis:** the case, counted at its latest status. Places are counties (or a county's courts) whose courts publish case-level records.

**Docket measures.** Counted per case at its latest status (`scripts/docket.py`): filings by plaintiff, month and court; plaintiff concentration; claim amounts; outcomes by plaintiff, kind of plaintiff and representation; plaintiff name lookup in `docs/docket/plaintiff_names.csv`.

## Requirements

### Pipeline

- R1. Download each source into a raw S3 bucket under dated keys, unchanged (except case-level court data, reduced under R15 before it is written). The raw bucket is versioned, with Object Lock (governance mode, 365 days) on every object; the first draft limited the lock to the CFPB prefix.
- R2. Normalize to Parquet in a curated bucket, partitioned by source and snapshot date.
- R4. Build the docket tables with SQL (Athena, with DuckDB for local development). Keep queries in the repo.
- R5. Every published number traces back to the snapshot dates and query that produced it.
- R15. **No personal identifiers for people sued.** Case-level court feeds are reduced in memory before anything is stored: defendant names, street addresses, the case style, and "judgment against" fields are dropped; only defendant ZIP and whether they had an attorney are kept. Plaintiffs (businesses) and their attorneys are kept. Tests enforce this.
- R16. **Alerts.** A weekly job compares each county's and each top plaintiff's filings with their own recent baseline and emails a short summary (SNS) when something moves well outside it. Thresholds live in the repo.
- R17. **Polite collection.** Each court source has a documented request rate and pause, honors its terms and robots.txt, and backs off on errors. No source is hit more often than it updates.
- R6. Report data quality on every run: rows read and kept, cases whose plaintiff name isn't in the lookup, and the year's case count against the state's published count.

### Outputs

- R7. A static docket page with charts and tables, published on GitHub Pages. _(Was a choropleth map; retired 2026-11-13.)_
- R8. A write-up (~1,500 words): the question, the method, the findings, the caveats, and what a legal aid program or court could do with it. `docs/docket/README.md` is the first draft.
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
EventBridge Scheduler: daily Harris County cases; monthly Texas OCA and Virginia
courts; quarterly Indiana courts
        │
        ▼
Ingest job (Lambda)
        │  writes dated, untouched files
        ▼
S3 raw  (versioned; Object Lock on every object)
        │
        ▼
Transform job (Python + DuckDB) ── Parquet, docket tables, DQ report
        │
        ▼
S3 curated (Parquet) ── Glue catalog ── Athena workgroup (scan cap)
        │
        ├── docket tables → static page (GitHub Pages)
        ├── weekly alert job → SNS email (R16)
        └── optional: read-only MCP server / notebook
```

Why AWS: the case-level feeds grow by roughly 100K+ debt cases a year for Harris County alone (OCA counted 91,823 in 2025; the first extract week, October 1–7, 2026, held 2,863), and need daily scheduling, a locked archive, and a query surface; county counts update monthly. Design choice: DuckDB inside the Fargate task does the heavy transforms (cheap and testable locally), and Athena is the shared query surface. Glue crawlers are skipped. Table definitions live in Terraform.

## Plan

Each phase ends with something you can show. Estimates assume part-time evenings.

### Phase 0: data checks (done 2026-11-07)

Phase 0 tested the earlier justice-gap framing before any infrastructure. Complaints failed as a need measure, LSC funding failed as a capacity measure, and Texas court data turned out to be the strongest source; the maintainer made the go call on 2026-11-07 with v1 as a debt-lawsuit monitor. The checks, scripts and results are in `docs/phase0/`; the county-map prototype that followed is in `docs/lawsuits/` and `docs/legal-aid/`. The literature search on Google Scholar and SSRN is still the maintainer's to do (`docs/phase0/literature-scan.md`).

### Phase 1: AWS bootstrap (run once locally with admin credentials)

- [x] Account hygiene, S3 Terraform state backend with `use_lockfile`, GitHub OIDC provider and plan/apply roles scoped to this repo
  _Applied 2026-11-08 (us-east-2, because of the account's organization region rule), with the trust policies updated the same day for GitHub's immutable OIDC subject format. Written in `infra/bootstrap/` with a runbook in `docs/aws-setup.md`; the maintainer applies it by hand. The bootstrap runs as a plain IAM admin user (no IAM Identity Center), a machine user whose access key exists only for the bootstrap and is deleted afterwards._
- [x] A GitHub `production` environment limited to `main`; `apply` runs on merge
  _Verified 2026-11-08: `plan` ran on a PR through OIDC, and the first apply-on-merge ran on `main`._
- [x] The permissions boundary for `claude-cloud-readonly` (R14). The user itself was later moved into the bootstrap too, with that policy as both its boundary and its only policy, so CI can't widen it.

Cloud sessions never get write access to AWS. Every change reaches AWS through Actions. After Phase 2 they can hold the read-only key from R14 for querying and debugging.

### Phase 2: pipeline infrastructure (~6–8 hours)

- [ ] Terraform under `infra/` _(storage and catalog done 2026-11-09; the first job, its schedule and its ingest role drafted 2026-11-11 in `infra/main/jobs.tf`: a daily Lambda for Harris County. Still to do: the state-count ingest jobs, the transform job, the transform and query roles. Plain files in one stack so far, not modules.)_: `storage` (raw/curated buckets, versioning, Object Lock, lifecycle), `catalog` (Glue database and tables, Athena workgroup with a 1 GB scan cap), `jobs` (ECR repo, Fargate task definitions, Lambda), `schedule` (EventBridge Scheduler), `iam` (the three roles from R12, plus the `claude-cloud-readonly` user from R14), `budget`
- [ ] After apply, the maintainer creates the read-only user's access key in the console and pastes it into the cloud environment's env vars (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`). Terraform must not create the key, so it never lands in state.
- [x] Threat model, one page, written **before** building: data integrity of the archive, IAM blast radius, and the public site (STRIDE)
  _Done 2026-11-09: `docs/threat-model.md`._
- [ ] CI: plan on PRs, apply on main, tflint + checkov

### Phase 3: ingest + transform (~8–10 hours)

- [ ] Court ingest jobs _(Harris County drafted 2026-11-11: `src/ingest_harris.py`, each run a snapshot of cases filed in the last 14 days)_: Harris County cases (daily, R15 applied in the job), Texas OCA counties (monthly), Virginia filing report (monthly), Indiana ICOR (quarterly). The fetch scripts in `scripts/lawsuits_fetch_*.py` and `scripts/phase0_tx_courts_fetch.py` are the starting point.
- [ ] Plaintiff name normalization (case, punctuation, "successor by merger" variants) as a versioned lookup table.
- [ ] Transform job: CSV → Parquet, build the docket tables, write the DQ report (R6)
- [ ] Local dev path: the same Python running against local files with DuckDB, plus a small fixture dataset for tests
- [ ] Turn on the schedule. Confirm a daily Harris County snapshot lands and is locked.

### Phase 4: analysis + outputs (~6–8 hours)

- [ ] Docket SQL (R4) on Athena, from the daily snapshots _(built locally 2026-11-12: `scripts/docket.py`)_
- [ ] Sanity checks: does the extract's yearly count match the state's (3.5% apart for 2025, not yet explained)? Do the plaintiff names and kinds hold up against a registry?
- [x] Static docket page (R7) _(2026-11-12, `scripts/docket_page.py`; the front page since 2026-11-13)_
- [ ] Draft the write-up (R8)

### Phase 5: publish

The repo is public from 2026-11-08, so the work is visible as it happens. Everything in it follows "Purely informational" above.

- [ ] Accuracy check on the docket and write-up (the page is already public): ask 1–3 people who know the field (LSC's data office, a legal aid program, a court data researcher) whether the data is read correctly and what would make it useful. This checks accuracy. It doesn't give anyone a veto.
- [ ] Publish the write-up (R8).

### Phase 6: optional extras

- [ ] Read-only query layer (R9): MCP server over Athena, showing the SQL it ran
- [ ] v2: a second place with case-level records (Virginia, or a high-rate Texas county), to see whether the Harris County patterns hold

**Total to a published v1:** roughly 30–40 hours after Phase 0.

## Success criteria

- A scheduled run refreshes everything with no manual steps
- At least 3 months of locked daily Harris County snapshots exist
- The docket and write-up are published, and at least one reader who knows the court or the field has reviewed them and called them useful or correct
- The maintainer can walk through the architecture, IAM, and the data caveats in 10 minutes

## Risks

| Risk | Likelihood | Mitigation |
| --- | --- | --- |
| Someone else builds the same thing (LSC's Civil Court Data Initiative, January Advisors) | Medium | Check what they publish for Harris County; aim to complement or contribute rather than duplicate |
| One county doesn't generalize | High | Say so on the page; add a second place before drawing broader conclusions |
| Scope creep into a web app | High | Static site only until v1 is published |
| A named plaintiff disputes a figure | Medium | Every figure comes from the court's records with its query; neutral words; the plaintiff name lookup is in the repo and marked not confirmed where it is |
| Court sites change layout or block automated access | Medium | Each fetcher checks expected columns and fails loudly (the Harris fetcher does); polite rates (R17); monthly sources tolerate a missed run |
| Personal data about people sued leaks or is retained | Low with R15 | Strip in memory before storage; tests; no defendant fields in the curated schema; threat model covers it |
| A figure reads as a judgment on legal aid (for example, the representation figures) | Low-medium | "Purely informational" rules (places, not programs; neutral words); describe records, not causes; Phase 5 accuracy check |

## Open questions

1. Why does the Harris County extract count 3.5% more 2025 cases than the state's report?
2. What does the attorney field include or miss (limited-scope help, debt-settlement firms)?
3. Which place comes second? Virginia's General District Court civil case files are available in bulk behind a sign-in at virginiacourtdata.org (`docs/manual-downloads.md`, item 1); whether they hold the fields the docket needs is not confirmed. A Texas county with heavy filing volume is the other option.
4. Is the education product the follow-on, with the docket picking where to start? The Harris County feed includes next hearing dates by court, which shows where and when people sued for debt are about to appear. The idea: a 30-second "what happens next" walkthrough reachable from the summons, for one case type in one jurisdiction.
