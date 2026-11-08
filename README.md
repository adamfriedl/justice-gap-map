# Justice Gap Map

**Where are debt-collection lawsuits filed, and where is civil legal aid thin?**

Debt collectors file hundreds of thousands of lawsuits a year in state courts. Most end in default judgments against people who never show up, often people who had a defense, or didn't know they could negotiate. This project pulls public court, credit, complaint, Census, and legal aid data into one place to show where that pressure falls and how it lines up with the help available.

It's a personal project: part research, part a working example of a small, reviewable data pipeline on AWS.

## What it shows so far

**Debt suits are surging** ([docs/lawsuits](docs/lawsuits/README.md)):
- Texas justice courts took 106,061 debt claims in 2014 and **518,852 in 2025**, up 33% from 2024 alone.
- Indiana collection cases rose from 67,683 (2014) to **140,846 (2024)**. **68%** of those disposed in 2024 ended in default judgments.

**Where they're filed isn't simply where the poverty is:**
- Indiana and Virginia suits concentrate where debt and poverty are high.
- Texas's highest rates are in fast-growing suburbs around Dallas–Fort Worth and Houston (Kaufman, Ellis, Brazoria), not the poor border counties.
- So no single national measure stands in for court data.

**Common proxies fail** ([docs/phase0](docs/phase0/)):
- *CFPB complaints* don't measure need. In Texas, the poorest counties have the most debt in collections and the fewest complaints, and complaint rates barely track lawsuit rates ([write-up](docs/phase0/complaints-vs-need.md)).
- *LSC funding* doesn't measure legal aid capacity. The federal formula is nearly flat per eligible person, while total legal aid nonprofit revenue runs from $18 to $275 per eligible person across states (outside DC) ([write-up](docs/phase0/lsc-funding-vs-capacity.md)).
- LSC's 130 service areas can be rebuilt as county sets, so county data can be compared with legal aid geography ([write-up](docs/phase0/lsc-data-availability.md)).

Every number in these write-ups names its source, its download date, and the script that produced it.

## How it's built

```
State courts (TX, IN, VA, Harris County)   ┐
Urban Institute debt in collections        │   Python + DuckDB         county / service-area
CFPB complaints, Census ACS, HUD ZIP map   ├─► (scripts/) ──────────►  tables, map, write-ups
LSC service areas, IRS nonprofit revenue   ┘
```

- **Today:** Python 3.12 scripts (managed with [uv](https://docs.astral.sh/uv/)) download each source and query it with [DuckDB](https://duckdb.org/). The CFPB file alone is ~6 GB, so no pandas.
- **Next:** the same jobs on AWS (S3, Athena, scheduled jobs). They refresh each source on its own schedule, keep dated snapshots, and flag unusual changes by county or plaintiff.
- **Infrastructure as code:** all of it is in Terraform under [`infra/`](infra/):
  - GitHub Actions authenticates to AWS with OIDC, so no AWS keys are stored anywhere.
  - Every PR shows a `terraform plan`, and merging to `main` applies it.
  - The deploy role has explicit guard rails: it can't change its own trust, the CI roles, or the state bucket.
  - Setup runbook: [docs/aws-setup.md](docs/aws-setup.md).
- **Built with AI coding agents under written rules.** [AGENTS.md](AGENTS.md) sets the limits:
  - read-only AWS access for agents;
  - no names or addresses of people sued, ever;
  - downloaded data treated as untrusted;
  - every data fact cited or marked "not confirmed".

## Privacy

People sued for debt are private individuals. Case-level court feeds are reduced in memory to non-identifying fields before anything is written: no names, no street addresses ([`scripts/lawsuits_fetch_harris.py`](scripts/lawsuits_fetch_harris.py), with a test). Only aggregate tables are committed.

## Repository

| Path | What |
| --- | --- |
| [`docs/prd.md`](docs/prd.md) | The plan: goals, data sources, metrics, phases |
| [`docs/lawsuits/`](docs/lawsuits/) | Debt-lawsuit counts by county (TX, IN, VA) and what they show |
| [`docs/phase0/`](docs/phase0/) | Data-validity checks: which measures hold up and which don't |
| [`scripts/`](scripts/) | Download and analysis scripts |
| [`infra/`](infra/) | Terraform: `bootstrap/` (state, CI roles, budget) and `main/` (pipeline) |
| [`tests/`](tests/) | Tests, including the privacy filter |

## Run it

```bash
uv sync
```

```bash
export CENSUS_API_KEY=...   # https://api.census.gov/data/key_signup.html
export HUD_API_TOKEN=...    # https://www.huduser.gov/portal/dataset/uspszip-api.html
```

Then follow the "Reproduce" steps in [docs/lawsuits/README.md](docs/lawsuits/README.md). Downloads go in `data/`, which is gitignored; raw data never goes in git. A few sources need a manual download: [docs/manual-downloads.md](docs/manual-downloads.md).

```bash
uv run pytest -q
```

## Status

- [x] **Phase 0:** data checks. Complaints and LSC funding failed as measures; debt in collections, court filings, and IRS revenue replaced them.
- [x] **Phase 1:** AWS bootstrap, Terraform state, and CI with OIDC.
- [ ] **Phase 2–4:** the pipeline on AWS, scheduled ingest, the map, and the write-up.
- [ ] **More states**, as their courts publish debt filings (Idaho is next).

The findings are descriptive. They show where need and resources diverge, not why, and they don't rank or judge individual legal aid programs.

## License

Code: [MIT](LICENSE). Data belongs to its sources (state courts, CFPB, Census Bureau, HUD, LSC, IRS, Urban Institute), under their own terms. The derived tables in `docs/` cite each one.
