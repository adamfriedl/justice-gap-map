# Manual downloads (things scripts can't fetch)

Last updated 2026-11-07. Each item says why a script can't get it and where it would go. None of these is blocking.

**How to get files to a cloud session:**
- Small files (under a few MB): attach them to a message.
- Larger files: keep them until the raw S3 bucket exists (Phase 2), then upload them to `raw/manual/<source>/<date>/`.
- **Never commit court case files to git.** They contain people's names.

| # | What | Where | Why manual | Use | Priority |
| --- | --- | --- | --- | --- | --- |
| 1 | **Virginia General District Court civil case files**, bulk, 2024 and 2025 | [virginiacourtdata.org](https://virginiacourtdata.org/) (free, sign in with Google) | Downloads sit behind a sign-in | Who sues in Virginia (plaintiffs by locality); a test of the 2025 "General Civil" proxy. Before use, strip defendant names and addresses (PRD R15). | High (the "who's suing" question) |
| 2 | **ABA ABArray state legal aid funding** | [ABArray page](https://www.americanbar.org/groups/legal_services/abarray-national-legal-aid-funding-data/) | americanbar.org returns 403 to scripts | Third check on the state ranking of total legal aid funding (`docs/phase0/lsc-funding-vs-capacity.md`) | Medium |
| 3 | **LSC per-grantee funding by source** | DataEase public "Grantee Funding" dashboard: [Tableau view](https://public.tableau.com/views/Grantee_Data_Page_Funding/GranteeFunding). Try Download → Data or Crosstab. | The CSV export isn't scriptable; whether a data download is enabled is **not confirmed** | All-source revenue per grantee, for resources below the state level | Medium |
| 4 | **LSC service-area boundary file** `LSC_basic_field_service_areas_08_17_2026.json` | Loaded by the [LSC grantee map](https://www.lsc.gov/about-lsc/our-grantees); open your browser's dev tools → Network, and save the JSON | The auto-mode safety check blocked the script fetch | Exact borders for the 8 split counties; not needed for county-set units | Low |
| 5 | **American Politics Research article**, DOI [10.1177/1532673X20962414](https://doi.org/10.1177/1532673X20962414) | Library or SAGE | Paywalled; the DOI resolver was blocked | Confirm title, authors, and findings cited in `docs/phase0/literature-scan.md` | Low |

**Not files, but worth an email:**
- **LSC Civil Court Data Initiative** (civilcourtdata@lsc.gov): case-level debt data for about 20 states via data-sharing agreement.
- **Dallas County district clerk**: its "Civil / Family Case Bulk Data Requests / Subscriptions" page, to ask whether justice-court debt claims are included.
