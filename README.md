# Debt Docket

**Who files debt-collection lawsuits, for how much, and how the cases end, counted from court records.**

Debt collectors file hundreds of thousands of lawsuits a year in state courts. Many end in default judgments against people who never show up, often people who had a defense or could have negotiated. This project reads the courts' own case records, starting with Harris County, Texas (Houston), and reports what they show about the plaintiffs and the cases. It never collects the names or addresses of the people sued.

It's a personal project: part research, part a working example of a small, reviewable data pipeline on AWS.

**[Open the Harris County docket →](https://adamfriedl.github.io/justice-gap-map/)**

## What it shows so far

**In Harris County, ten companies file three quarters of the debt claims** ([docs/docket](docs/docket/README.md)):
- 206,858 debt claims were filed in the county's justice courts from January 2025 to November 10, 2026. Ten plaintiffs filed 75.4% of them, and companies that buy unpaid accounts filed 63.0%.
- The median claim is $3,667.
- Of cases filed in 2025, 11.9% have an attorney recorded for the defendant. 2.7% of those ended in a default judgment, against 25.0% of the rest. That describes the records; it doesn't show what an attorney changes.

**For scale, from statewide court counts** ([docs/lawsuits](docs/lawsuits/README.md)):
- Harris County's 91,823 debt claims in 2025 were 17.7% of the 518,852 filed in Texas justice courts that year (Texas Office of Court Administration, downloaded 2026-11-06 and 2026-11-07).
- Texas debt claims rose from 106,061 in 2014 to 518,852 in 2025, up 33% from 2024 alone. Indiana collection cases rose from 67,683 (2014) to 140,846 (2024).

These counts are context, not comparisons: each state defines and reports debt cases its own way.

Every number names its source, its download date, and the script that produced it.

### Where the project started

It began as a "justice gap" map setting debt pressure against legal aid, by county and LSC service area. The early data checks ([docs/phase0](docs/phase0/)) found that the usual proxies don't hold up: CFPB complaints don't track need, and LSC funding doesn't measure legal aid capacity. The county map that followed had rates that couldn't be compared across states, so it was retired on 2026-11-13 in favor of the docket. Those write-ups stay in the repository: [docs/phase0](docs/phase0/), [docs/lawsuits](docs/lawsuits/README.md), and [docs/legal-aid](docs/legal-aid/texas.md) (Texas legal aid offices next to debt suits).

## How it's built

```
Harris County case extract (daily)  ─┐
                                     ├─►  Python + DuckDB  ─►  docket tables, page, write-up
State court counts (TX, IN, VA)     ─┘
```

- **So far (as of November 2026):** Python 3.12 scripts (managed with [uv](https://docs.astral.sh/uv/)) download each source and query it with [DuckDB](https://duckdb.org/). The Harris County extract is also pulled daily on AWS into a locked archive.
- **Next:** build the docket tables on AWS from that archive, so the page rebuilds without a local download.
- **Built with AI coding agents under written rules.** [AGENTS.md](AGENTS.md) sets the limits:
  - read-only AWS access for agents;
  - no names or addresses of people sued, ever;
  - downloaded data treated as untrusted;
  - every data fact cited or marked "not confirmed".

### Infrastructure

All of it is Terraform in [`infra/`](infra/), in two stacks.

| Stack | What it holds | How it changes |
| --- | --- | --- |
| [`infra/bootstrap/`](infra/bootstrap/) | Terraform's state bucket; the link that lets GitHub Actions sign in to AWS (OIDC); the two CI roles; the ceiling on what AI agents can do; a monthly budget alert | Rarely. Applied by hand by the maintainer, with a temporary key that's deleted afterward ([runbook](docs/aws-setup.md)) |
| [`infra/main/`](infra/main/) | The pipeline: data buckets, query engine (Athena), scheduled jobs. So far: the buckets, Athena, and the first job, a daily Harris County download. | Through pull requests only |

**How an infrastructure change ships:**
1. A pull request changes something in `infra/main/`.
2. GitHub Actions signs in to AWS with a short-lived token (OIDC) and posts `terraform plan`, a preview of exactly what will change. The plan role is read-only.
3. The maintainer reads the plan and merges. Merging is the approval.
4. Actions runs `terraform apply` on `main` with the apply role.

No AWS keys are stored in GitHub or anywhere else. The apply role is admin-level because it builds the pipeline, but explicit denies stop it from changing its own trust, the CI roles, the agents' ceiling, or the state bucket. A bad merge can break the pipeline, but it can't take over the account.

**How the data will update (planned):**
- Each source gets its own scheduled job, on the source's own rhythm: Harris County cases daily (running now), Texas and Virginia court counts monthly, Indiana quarterly.
- Raw downloads are kept as dated snapshots, locked against deletion, so every number can be traced to the file it came from.
- A weekly job compares each large plaintiff's filings with its own recent weeks and emails a summary when one moves well outside them.
- Idle cost is near zero, with a budget of about $10/month.

## Why Harris County

There's no national count of debt lawsuits, and very few courts publish case-level records a script can read. Harris County's justice courts do: a daily public extract with the plaintiff, its attorney, the filing date, the claim amount, hearings, and how each case ended. It's also big, about one in six Texas debt claims.

Statewide counts give the context around it:

| State | What the courts publish | What it's used for |
| --- | --- | --- |
| **Texas** | A "Debt Claim" case type in justice courts since 2013, with county counts of filings, defaults, and dispositions ([OCA](https://card.txcourts.gov/)) | Scale, a check on the Harris County extract's counts, and where to look next |
| **Indiana** | A "Collection" case type with county counts ([ICOR](https://publicaccess.courts.in.gov/ICOR/)) | A clean statewide series with default judgments |
| **Virginia** | Monthly General District Court filing reports (PDF) | Court-level counts; Virginia may also publish case-level data (not confirmed) |

## Privacy

People sued for debt are private individuals. Case-level court feeds are reduced in memory to non-identifying fields before anything is written: no names, no street addresses ([`scripts/lawsuits_fetch_harris.py`](scripts/lawsuits_fetch_harris.py), with a test). Only aggregate tables are committed.

## Repository

| Path | What |
| --- | --- |
| [`docs/prd.md`](docs/prd.md) | The plan: goals, data sources, phases |
| [`docs/docket/`](docs/docket/) | The Harris County docket: who files, for how much, how cases end |
| [`docs/lawsuits/`](docs/lawsuits/) | Statewide debt-lawsuit counts (TX, IN, VA), used as context |
| [`docs/legal-aid/`](docs/legal-aid/) | Earlier work: Texas legal aid offices set next to debt suits |
| [`docs/phase0/`](docs/phase0/) | Earlier work: which measures held up and which didn't |
| [`scripts/`](scripts/) | Download and analysis scripts |
| [`site/`](site/) | The published page (the Harris County docket); rebuilt with `scripts/docket_page.py` |
| [`infra/`](infra/) | Terraform: `bootstrap/` (state, CI roles, budget) and `main/` (pipeline) |
| [`tests/`](tests/) | Tests, including the privacy filter |

## Run it

```bash
uv sync
```

The docket: follow "Reproduce" in [docs/docket/README.md](docs/docket/README.md). The statewide counts: follow "Reproduce" in [docs/lawsuits/README.md](docs/lawsuits/README.md). Downloads go in `data/`, which is gitignored; raw data never goes in git. A few sources need a manual download: [docs/manual-downloads.md](docs/manual-downloads.md).

```bash
uv run pytest -q
```

## Where it stands

Done as of November 2026:
- The Harris County docket: who files, for how much, and how cases end, published as the project's page.
- A daily Harris County download on AWS into a locked archive, and the AWS foundation under it: Terraform state, CI that signs in with OIDC, plan on every PR, apply on merge.
- Statewide debt-suit counts for Texas, Indiana and Virginia.
- Earlier: data checks that retired complaints and LSC funding as measures, Texas legal aid offices next to debt suits, and a county map (retired 2026-11-13).

**Next steps** (the full list is in [docs/docket](docs/docket/README.md#next-steps)):
- Build the docket tables on AWS from the daily archive, and re-pull older months so late outcomes are caught.
- A weekly alert when a large plaintiff's filings move well outside its own recent weeks.
- A second place with case-level records. Virginia comes first; Texas counties with heavy filing volume are the other option.

**Possible later:**
- A plain-English question box over the data that shows the query it ran.
- The long-term aim: plain-language guides to the debt-suit process for people who've been sued. The Harris County extract has hearing dates by court, which shows where and when people are due to appear.

The project is purely informational. It reports what public records show, not why, and it doesn't call out or judge legal aid providers or their funders. The businesses that file the suits are named, with every figure sourced to court records.

## License

Code: [MIT](LICENSE). Data belongs to its sources (state courts, CFPB, Census Bureau, HUD, LSC, IRS, Urban Institute), under their own terms. The derived tables in `docs/` cite each one.
