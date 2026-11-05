# AGENTS.md

Guidance for AI coding agents, including Claude Code cloud sessions.

## What this repo is

A data pipeline and map joining CFPB debt-collection complaints, LSC legal aid funding, and Census ACS data to show where consumer-debt harm is high and legal aid is thin. The plan and current phase are in `docs/prd.md`. Read it first.

## Rules

- **Never run `terraform apply` or any command that changes AWS.** Cloud sessions have no AWS credentials, by design. Infra changes go through a PR, where GitHub Actions runs `plan`, and `apply` runs on main after manual approval.
- **Terraform under `infra/` is hand-written by the maintainer.** Review it, explain it, and suggest changes in PR comments or chat. Don't author or rewrite it unless the maintainer asks you to in that session.
- **Raw data never goes in git.** Downloads go under `data/` (gitignored). Commit only small derived results: summary tables, data-quality reports, and notes under `docs/`.
- **No secrets in the repo.** `CENSUS_API_KEY` and `HUD_API_TOKEN` come from the environment. If one is missing, say so and stop that step. Don't hardcode a workaround.
- **Be descriptive, not causal.** Findings describe where need and resources diverge. Don't rank or criticize individual legal aid programs.
- **Show your work.** Every number in a write-up names its source snapshot date and the query or script that produced it.
- **Data-source facts need a citation.** If you can't confirm something about a dataset (fields, geography, masking rules), mark it "not confirmed" rather than guessing.

## Stack

- Python 3.12, managed with `uv`. DuckDB for local analysis. Keep dependencies few; add one only when it earns its place.
- Terraform ≥ 1.10 on AWS (later phases).

## Verify

Before claiming done:

```bash
uv run python -m compileall -q src scripts
uv run pytest -q   # once tests exist
```

For Terraform (once `infra/` exists): `terraform fmt -check -recursive infra && terraform -chdir=infra validate`.

## Network hosts this project uses

`files.consumerfinance.gov`, `www.consumerfinance.gov`, `cfpb.github.io`, `api.census.gov`, `www.census.gov`, `www2.census.gov`, `www.huduser.gov`, `www.lsc.gov`, `www.lscdataease.org`, and PyPI. If a request is blocked, report which host so the environment allowlist can be updated.
