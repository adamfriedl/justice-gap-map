# Threat model

_Written 2026-11-09, before the pipeline is built, as the PRD asks. One page; revisit when jobs, schedules or a query layer are added._

**What's worth protecting:**
1. **The raw archive.** Dated snapshots that every published number traces back to (R5). The CFPB copy may become the only one if the public data is restricted.
2. **The published numbers and map** on GitHub Pages.
3. **Privacy of people sued.** No names or street addresses are ever stored (R15).
4. **The AWS account:** its bill, and its ability to act.

**Who or what could cause harm:** someone on the internet (the repo and the map are public); a compromised GitHub account or a bad merge; a leaked read-only key from a cloud session; hostile content inside downloaded data; a source that changes or withdraws its data.

## STRIDE, by area

| | Archive integrity (raw bucket) | IAM blast radius | Public site |
| --- | --- | --- | --- |
| **Spoofing** | Fake files written as if from a source: only the ingest role can write to raw (next PR), and it fetches over HTTPS from fixed hosts. | Someone assumes the CI roles: only this repo's OIDC tokens, `pull_request` (read-only plan role) or the `production` environment limited to `main` (apply role). No long-lived AWS keys exist. | A look-alike site: out of scope. The repo links the one URL. |
| **Tampering** | A snapshot is changed or deleted later: versioning plus Object Lock (governance, 365 days). Only admin roles hold `s3:BypassGovernanceRetention`; job roles and the read-only user won't. | A merge widens the read-only user's policy: the bootstrap permissions boundary caps it, and the apply role can't edit the boundary. A merge edits the CI roles or state bucket: explicit denies on the apply role. | The map's numbers are changed: `site/` changes only by merge to `main`; the build is reproducible from committed CSVs and scripts. |
| **Repudiation** | Who changed what: S3 versions keep every write; CloudTrail event history keeps 90 days of management calls. **Gap:** S3 data-event logging (object reads and writes) is off; it costs money. Revisit if the archive matters as evidence. | Who applied what: every apply is a GitHub Actions run tied to a merge commit. | Every change to the site is a commit. |
| **Information disclosure** | Raw holds only public data, plus case-level court data already stripped of names and addresses before writing (R15, tested). Buckets block all public access and refuse non-TLS requests. | A leaked read-only key reads only project buckets and Athena results, which hold public data. Rotate it every 90 days; delete it on any suspicion. | Public by design. Only aggregates are published. |
| **Denial of service** | A runaway ingest fills the bucket: the budget alert covers the whole account ($10/month, alerts at 80%). | Runaway Athena queries: the 1 GB per-query scan cap means $0.005 a query at most. | GitHub Pages availability: accepted. |
| **Elevation of privilege** | Hostile content in a download (e.g. instructions in complaint narratives or web pages): treated as data. Agents are told so (AGENTS.md), and the jobs parse it and never execute it. | The apply role is admin-level by necessity. Limits: OIDC trust is pinned to `main` through the environment; guard rails protect its own trust; the maintainer reads every plan before merging. **Accepted risk:** a malicious merge could create new admin resources. | The page loads d3 and topojson from cdnjs. **Gap:** no Subresource Integrity hashes yet. Add them, or vendor the two files. |

## Decisions and follow-ups

- **Object Lock covers the whole raw bucket, not just `cfpb/`.** It's simpler, and every raw file is meant to be immutable (R1).
- **No customer-managed KMS keys.** The data is public; SSE-S3 avoids key-policy complexity.
- **Follow-ups:** add SRI hashes to the map page's two scripts. Decide on S3 data-event logging once the archive has history. The job roles (R12) come with the jobs, each with write access only to its own prefix and no `BypassGovernanceRetention`.
