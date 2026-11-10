# REVIEW.md

What matters when reviewing changes here. Project rules are in `AGENTS.md`.

## What failure looks like

- **It leaks people.** A name or street address of someone sued gets written anywhere: disk, logs, S3, git, or a derived table.
- **It lies with numbers.** A metric is computed wrong (bad join, county/service-area mismatch, double counting, wrong ACS vintage). Or a number in a write-up doesn't name its source snapshot and the query that produced it.
- **It editorializes.** A write-up says why instead of what the records show. It names, ranks, or criticizes legal aid providers or funders instead of places. Or it names a plaintiff without citing the court records behind the claim. (See "Purely informational" in `AGENTS.md`.)
- **It over-grants.** Terraform or IAM gives more access than the change needs, or Actions workflows gain permissions or secrets.
- **It commits what it shouldn't.** Raw data, large files, or credentials end up in git.

## Focus

- Correctness of joins and geography (FIPS codes, county sets per LSC service area).
- The PII-stripping path and its test.
- Every IAM statement in `infra/`, and the OIDC trust conditions.

## Skip

- `data/` (gitignored), `uv.lock`, and generated files under `docs/phase0/` beyond spot-checking that the numbers match their script.
- Formatting and import order.
