# Justice Gap Map: PRD and plan

_Drafted 2026-11-05. Working name. Gated on the Phase 0 go/no-go._

## Summary

A small, repeatable data pipeline on AWS that joins three public datasets:

- CFPB consumer complaints, starting with debt collection
- Legal Services Corporation (LSC) grantee funding and caseloads
- Census ACS demographics

It answers one question: **where are people taking the most consumer-debt harm while having the least civil legal aid?** The outputs are a published map, a short write-up, and an optional plain-English query layer in the style of [civicaitools.org](https://civicaitools.org/).

The longer-term goal is legal-process education for people who default on a complaint out of fear, or who show up and get bulldozed because they don't know the process. This map shows where that help is needed most.

## Problem

- Debt collection cases end in default more than 70% of the time (Pew, 2020). Many defendants had a defense or could have negotiated.
- People often don't recognize these problems as legal (Sandefur, ABF), so they never look for help.
- Civil legal aid is scarce and unevenly funded. LSC's Justice Gap studies document the unmet need nationally, but it's hard to see at a local level.
- Each piece is public, but the datasets don't line up. CFPB uses ZIP codes, LSC uses service areas, and ACS uses tracts and counties. Nobody has put them in one place. (A quick search on 2026-11-05 found no published combination. It wasn't a thorough check.)

## Audience

| Who | What they get |
| --- | --- |
| Legal aid program and development staff | Evidence for grant applications and for deciding where to do outreach |
| A2J researchers and funders (LSC, state IOLTA, legal design labs) | A reproducible local view of need vs. resources |
| Civic tech and open-data people | A worked example of joining mismatched federal datasets |

## Goals

1. **One defensible finding.** For example: "These N service areas have the highest debt-collection complaint rate per eligible resident and the lowest LSC funding per eligible resident." It must hold up to a legal-aid reader's scrutiny.
2. **Reproducible and refreshable.** One command (or a schedule) pulls new data, rebuilds the tables, and regenerates the map. No manual steps.
3. **An independent archive.** Keep dated, unchangeable snapshots of the CFPB data. The CFPB has been politically exposed since 2025, and an archive matters if the public data is restricted.
4. **All infrastructure in Terraform on AWS**, written to be read: the maintainer reviews every infra PR and can explain it in 10 minutes.
5. **Cheap.** Idle cost near $0, and under ~$10/month while active.

## Non-goals (v1)

- Court records or lawsuit data. CFPB complaints are a stand-in for consumer harm, not for lawsuits. Court data is a v2 question.
- Products other than debt collection. The pipeline should handle any product, but only debt collection gets analyzed.
- Causal claims. This is descriptive: it shows where need and resources diverge, not why.
- Ranking or criticizing individual legal aid programs.
- A polished web app. A static map plus a write-up is enough.
- The education product itself. This project picks where it should go first.

## Data sources

| Source | What | Geography | Refresh | Known issues |
| --- | --- | --- | --- | --- |
| [CFPB Consumer Complaint Database](https://www.consumerfinance.gov/data-research/consumer-complaints/) | Every published complaint: product, issue, company, date, state, ZIP, company response, optional narrative | 5-digit ZIP, 3-digit ZIP, or blank | Daily | ZIP is shortened or hidden for small-population areas, and the rules differ between docs ([field reference](https://cfpb.github.io/api/ccdb/fields.html), [data-use page](https://www.consumerfinance.gov/complaint/data-use/)). Only people who know about the CFPB file, so expect awareness bias. The data may not continue. |
| [LSC research & data](https://www.lsc.gov/research-data), [service areas](https://www.lsc.gov/grants-grantee-resources/our-grant-programs/basic-field-grant/lsc-service-areas), [DataEase](https://www.lscdataease.org/) | Grantee funding and Grantee Activity Report case closures | LSC service area (usually made of counties; **not confirmed**) | Annual | **Downloadable boundaries and grantee data not yet confirmed.** This is the riskiest source. |
| Census ACS 5-year (API) | Population at or below 125% of poverty (LSC's eligibility line), renters, limited English, broadband, age | Tract, county, ZCTA | Annual | Margins of error get large in small areas |
| [HUD-USPS ZIP crosswalk](https://www.huduser.gov/portal/datasets/usps_crosswalk.html) | Weights for converting ZIP ↔ county/tract | ZIP → county | Quarterly | Use the file that goes in the right direction. Some ZIPs are missing. Needs a registered API token. |

**Unit of analysis:** the LSC service area if Phase 0 confirms boundaries can be built (probably as sets of counties). Fall back to county otherwise, attaching LSC funding where a service area maps cleanly to counties.

**Core metrics** (all per eligible resident, using the ACS 125%-of-poverty population):

- Debt-collection complaints per 10K eligible residents, over a rolling window (e.g. trailing 3 years)
- LSC basic field funding per eligible resident
- LSC case closures per eligible resident, if the data allows
- A simple **gap score**: high complaint rate plus low funding (rank-based, and explained in plain words, not a black box)
- Context columns: share of renters, share with limited English, share without broadband

## Requirements

### Pipeline

- R1. Download each source into a raw S3 bucket under dated keys, unchanged. The raw bucket is versioned, and the CFPB prefix has Object Lock (governance mode).
- R2. Normalize to Parquet in a curated bucket, partitioned by source and snapshot date.
- R3. Write geography crosswalks (ZIP → county → service area) once per snapshot and version them.
- R4. Build the metric tables with SQL (Athena, with DuckDB for local development). Keep queries in the repo.
- R5. Every published number traces back to the snapshot dates and query that produced it.
- R6. Report data quality on every run: how many complaints were dropped for missing or 3-digit ZIPs, broken down by state, and how many ZIPs the crosswalk couldn't match.

### Outputs

- R7. A static choropleth map with a sortable table, published on GitHub Pages.
- R8. A write-up (~1,500 words): the question, the method, the finding, the caveats, and what a legal aid program could do with it.
- R9. Optional: a read-only query layer, either an MCP server over the curated tables or a small notebook. It shows the SQL it ran.

### Infrastructure

- R10. All of it in Terraform: S3 (raw and curated), Glue catalog, an Athena workgroup with a scan limit, IAM roles, an EventBridge Scheduler schedule plus the job runner, Parameter Store, a budget alarm.
- R11. GitHub Actions authenticating through OIDC. `terraform plan` on PRs; `apply` on main behind a GitHub environment that needs manual approval.
- R12. Least privilege: the ingest role writes only to raw, the transform role reads raw and writes curated, the query role is read-only on curated.
- R13. Scales to zero when idle. No always-on compute.
- R14. **Read-only cloud-session access.** An IAM user `claude-cloud-readonly`, defined in Terraform, whose access key lives only in the Claude Code cloud environment's env vars. It may:
  - read the raw and curated buckets (`s3:GetObject`, `s3:ListBucket`)
  - run Athena queries in the project workgroup only, writing results only to an `athena-scratch/` prefix (the one write it has), and read the Glue catalog
  - read the project's CloudWatch logs and ECS/Lambda job status

  It has no IAM, no resource creation or deletion, no access to other buckets, and no writes to raw or curated. A permissions boundary caps it even if its policy is later loosened by mistake. Keys are rotated at least every 90 days and on any suspicion. Its access must be visible in CloudTrail.

## Architecture (v1)

```text
EventBridge Scheduler (weekly CFPB, quarterly HUD, annual ACS/LSC)
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
        └── optional: read-only MCP server / notebook
```

Design choice: DuckDB inside the Fargate task does the heavy transforms (cheap and testable locally), and Athena is the shared query surface. Glue crawlers are skipped. Table definitions live in Terraform.

## Plan

Each phase ends with something you can show. Estimates assume part-time evenings.

### Phase 0: data spikes and gap check (1–2 evenings, before any infra)

This decides whether the project is viable. No AWS needed, so it suits cloud sessions. Raw downloads stay out of git. Commit only small results (tables, notes) under `docs/phase0/`.

- [ ] **LSC:** find out exactly what's downloadable: service area boundaries or their county lists, funding by grantee or service area, and GAR case closures. If service areas can't be rebuilt from counties, switch the unit to county and write the reason down.
- [ ] **CFPB:** download the full CSV. Measure the share of debt-collection complaints with a 5-digit ZIP, a 3-digit ZIP, or none, by state. If more than ~30% can't be placed, reconsider the unit (state, or 3-digit ZIP areas).
- [ ] **Crosswalk:** pull HUD ZIP→county and check how many complaint ZIPs it matches.
- [ ] **Gap check, done properly:** search Google Scholar and SSRN. Check LSC's own reports, the NCSC, Pew, January Advisors (debt lawsuit data), and the Stanford Legal Design Lab and Suffolk LIT Lab sites. If someone already did this, look for what they left out or contribute to their work instead.
- [ ] **One hand-built prototype:** a single state (pick one with clean ZIPs and county-based service areas) in DuckDB. Does any signal show up?

**Go/no-go:** continue if LSC data can be attached to some geography, more than ~70% of complaints can be placed, and nobody has already published this. Otherwise write down why in `docs/phase0/` and stop.

### Phase 1: AWS bootstrap (run once locally with admin credentials)

- [ ] Account hygiene, S3 Terraform state backend with `use_lockfile`, GitHub OIDC provider and plan/apply roles scoped to this repo
- [ ] A GitHub `production` environment with required reviewers, so `apply` needs approval
- [ ] The permissions boundary for `claude-cloud-readonly` (R14). The user and its scoped policy land in Phase 2, once the buckets and workgroup exist.

Cloud sessions never get write access to AWS. Every change reaches AWS through Actions. After Phase 2 they can hold the read-only key from R14 for querying and debugging.

### Phase 2: pipeline infrastructure (~6–8 hours)

- [ ] Terraform modules under `infra/`: `storage` (raw/curated buckets, versioning, Object Lock, lifecycle), `catalog` (Glue database and tables, Athena workgroup with a 1 GB scan cap), `jobs` (ECR repo, Fargate task definitions, Lambda), `schedule` (EventBridge Scheduler), `iam` (the three roles from R12, plus the `claude-cloud-readonly` user from R14), `budget`
- [ ] After apply, the maintainer creates the read-only user's access key in the console and pastes it into the cloud environment's env vars (`AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, `AWS_REGION`). Terraform must not create the key, so it never lands in state.
- [ ] Threat model, one page, written **before** building: data integrity of the archive, IAM blast radius, and the public site (STRIDE)
- [ ] CI: plan on PRs, apply on main, tflint + checkov

### Phase 3: ingest + transform (~8–10 hours)

- [ ] Ingest jobs for CFPB, ACS, the HUD crosswalk, and LSC (LSC may start as a manual drop into raw, which is fine for annual data; document it)
- [ ] Transform job: CSV → Parquet, apply the crosswalk, write the DQ report (R6)
- [ ] Local dev path: the same Python running against local files with DuckDB, plus a small fixture dataset for tests
- [ ] Turn on the schedule. Confirm a weekly CFPB snapshot lands and is locked.

### Phase 4: analysis + outputs (~6–8 hours)

- [ ] Metric SQL (R4) and gap score
- [ ] Sanity checks: does the national total match published CFPB counts? Does total LSC funding match published totals? Do the top-ranked areas make sense to someone who knows the region?
- [ ] Static map + table (R7)
- [ ] Draft the write-up (R8)

### Phase 5: share privately, then publish

Findings about legal aid funding can read as criticism, so the people affected see them first. The repo stays private until this phase is done.

- [ ] Send the draft to 1–3 legal aid or A2J reviewers, including someone at LSC's data office and a legal aid program in a top-ranked area. Ask what's wrong and what would make it useful.
- [ ] Revise, make the repo public, and publish the map and write-up.

### Phase 6: optional extras

- [ ] Read-only query layer (R9): MCP server over Athena, showing the SQL it ran
- [ ] Add a second CFPB product (credit reporting, mortgages)
- [ ] v2: court-side data for a state with open debt-lawsuit records, to test whether complaint rates track default rates

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
| LSC data is too coarse or not downloadable | Medium-high | Phase 0 spike; fall back to county or state; ask LSC's data office directly |
| CFPB ZIP masking hides too much in rural areas | Medium | Measure in Phase 0; report it openly; use 3-digit ZIP areas or state for affected regions |
| CFPB data restricted or discontinued | Medium | Archive from week one. If it happens, the archive becomes the story. |
| The finding just matches "poor places have less help" | Medium | Still useful locally. Look for surprises (well-funded areas with high complaint rates, and the reverse). Say so plainly if nothing surprising shows up. |
| Scope creep into a web app | High | Static site only until v1 is published |
| The finding reads as an attack on LSC or grantees | Low-medium | Phase 5 private review; frame it as "where more help is needed," not "who is failing" |

## Open questions

1. What unit of analysis can the LSC data actually support? (Phase 0)
2. Is a 3-year complaint window right, or should it be by year to show trends? Decide after seeing the data.
3. Is there a state with open debt-collection court data good enough for the v2 check? January Advisors' Texas work is the first place to look.
4. Is the education product the follow-on, with this map picking where to start? The idea: a 30-second "what happens next" walkthrough reachable from the summons, for one case type in one jurisdiction.
