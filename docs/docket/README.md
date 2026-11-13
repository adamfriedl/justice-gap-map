# The Harris County debt docket

_Built 2026-11-11. Scripts: [`scripts/docket.py`](../../scripts/docket.py) (tables) and [`scripts/docket_page.py`](../../scripts/docket_page.py) (page). Page: [site/docket](../../site/docket/index.html), published with the map._

Who files debt claims in Harris County's justice courts, for how much, and how the cases end. Everything here is counted from the county's own case records. Nothing is estimated, and there are no population or legal aid figures in it.

**Source and snapshot.** [Harris County Justice Courts public data extract](https://jpwebsite.harriscountytx.gov/PublicExtracts/search.jsp), "cases filed" extract, case type Debt Claim, all 16 courts. Downloaded 2026-11-11 with [`scripts/lawsuits_fetch_harris.py`](../../scripts/lawsuits_fetch_harris.py), one month per request, for filing dates 2025-01-01 to 2026-11-10. Defendants' names and street addresses are dropped in memory before anything is written (PRD R15). Every number below is from that download and `scripts/docket.py`.

## What it shows

**Volume** ([`summary.csv`](summary.csv), [`by_month.csv`](by_month.csv))
- 206,858 debt claims were filed from January 2, 2025 to November 10, 2026: 94,999 in 2025 and 111,859 so far in 2026.
- Monthly filings rose from about 5,300–8,000 in the first half of 2025 to about 10,000–11,800 from June to October 2026. February 2026 was the highest month, at 13,259.
- The median claim is $3,667. Claims total $1.03 billion, $498 million of it in cases filed in 2025. 6,412 cases have no claim amount.

**Who files** ([`by_plaintiff.csv`](by_plaintiff.csv))
- Ten plaintiffs filed 75.4% of the cases. There are 843 plaintiffs after combining spellings (2,152 names as typed).
- The five largest: LVNV Funding (30,450 cases, 14.7%), Portfolio Recovery Associates (27,956, 13.5%), Midland Credit Management (24,032, 11.6%), Capital One (20,226, 9.8%) and Jefferson Capital Systems (16,573, 8.0%).
- Plaintiffs this project groups as debt buyers filed 63.0% of the cases. Their median claims are lower ($2,814 for 2025 cases) than banks' and card issuers' ($5,740).
- LVNV Funding and Portfolio Recovery Associates each filed nearly twice as many cases in 2026 to date as in all of 2025 (19,908 against 10,542; 18,185 against 9,771).
- Five plaintiff attorneys' names are on 28.7% of the cases. Individual attorneys aren't listed here.

**How 2025 cases ended** (as of 2026-11-11; [`outcomes_by_kind_2025.csv`](outcomes_by_kind_2025.csv), [`outcomes_by_plaintiff_2025.csv`](outcomes_by_plaintiff_2025.csv))

| Kind of plaintiff | Filed in 2025 | Default judgment | Dropped by plaintiff | Agreed judgment | Dismissed, not pursued | Trial or other | Still open |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Debt buyer | 53,661 | 24.5% | 28.0% | 8.1% | 6.9% | 7.5% | 25.0% |
| Bank or card issuer | 33,708 | 20.8% | 27.6% | 12.8% | 8.5% | 6.3% | 24.0% |
| Consumer lender | 3,618 | 12.9% | 13.5% | 14.8% | 10.8% | 5.4% | 42.6% |
| Auto lender | 1,203 | 15.5% | 38.4% | 2.4% | 12.4% | 4.3% | 27.0% |
| Other or not classified | 2,809 | 16.3% | 26.1% | 5.8% | 11.0% | 8.6% | 32.2% |

**Representation** ([`outcomes_by_representation_2025.csv`](outcomes_by_representation_2025.csv))
- An attorney is recorded for the defendant in 11,300 of the 94,999 cases filed in 2025 (11.9%).
- Of those cases, 2.7% ended in a default judgment and 33.3% in an agreed judgment. Of the 83,699 with no attorney recorded, 25.0% ended in a default judgment and 6.7% in an agreed judgment.
- This describes the records. It doesn't show what an attorney changes: people who hire one differ from people who don't.

**Courts** ([`by_court_2025.csv`](by_court_2025.csv))
- The 16 courts close cases at very different speeds. In Precinct 5, Place 2, 2.1% of 2025 cases are still open; in Precinct 3, Place 1, 65.4% are.
- Default judgments range from 0.0% to 42.1% of 2025 filings by court. Most of that range follows how many cases a court has closed.

## How cases are counted

- **One row per case.** The extract has one row per case and party (215,332 rows for 206,858 cases). Rows are collapsed by case number. A case counts as having a defendant's attorney if any of its rows names one.
- **Latest status.** When a case appears in more than one download, the rows from the latest download are used.
- **Outcomes are shares of all cases filed in 2025,** including those still open, so the columns add to 100%. All 2025 cases are at least ten months old. Cases filed in 2026 aren't in the outcome tables: most are still open.
- **Outcome groups** follow the courts' disposition field: "Default Judgment"; "Non-suited or Dismissed by Plaintiff" (dropped by plaintiff); "Agreed Judgment"; "Dismissed for Want of Prosecution" (dismissed, not pursued); "Trial or Hearing by Judge" and all other dispositions, including appeals and transfers (trial or other); blank (still open).
- **ZIP codes** ([`by_zip_2025.csv`](by_zip_2025.csv)): defendants' ZIP codes with at least 50 cases filed in 2025, with the share still open and the share with an attorney. Outcome shares are left out, because a ZIP's cases mostly go to one court and would mostly show that court's pace.

## Plaintiff names

The same company is typed many ways ("LVNV Funding, LLC", "Lvnv Funding Llc", "LVNV FUNDING LLC,"). `clean_plaintiff()` in the script upper-cases a name, removes punctuation, cuts everything after "assignee of", "successor by merger to", "successor in interest to", "trust manager for" and "d/b/a", and removes company suffixes. [`plaintiff_names.csv`](plaintiff_names.csv) then gives each key a display name and a kind, and fixes misspellings found in the records.

- **The lookup is this project's work,** and changes to it are changes to the results. It covers the plaintiffs behind 97.1% of cases; the rest are "other or not classified".
- **Kinds (debt buyer, bank or card issuer, consumer lender, auto lender) come from company names.** They aren't from a registry and haven't been checked against one: **not confirmed**.
- **Capital One includes cases it filed as successor to Discover Bank** (10,225 cases name Discover that way). Cases filed in Discover Bank's own name (1,559, all in 2025) are counted separately.
- Cutting at "assignee of" attributes a case to the company that filed it, not the original lender. Cavalry SPV I's 5,055 cases, for example, name several original lenders.

## Checks

- **Against the state's count.** The Texas Office of Court Administration reports 91,823 debt claims filed in Harris County justice courts in 2025 ([`docs/lawsuits/county_filings_tx_in.csv`](../lawsuits/county_filings_tx_in.csv), downloaded 2026-11-06 and 2026-11-07). This extract has 94,999 for the same year, 3.5% more. Why they differ is **not confirmed**; the state figure comes from monthly court reports at 99% reporting, and the extract is a live case list.
- **Every row is a Debt Claim case** (case type field), and no case has more than one plaintiff name or more than one defendant ZIP across its rows.
- Tests: [`tests/test_docket.py`](../../tests/test_docket.py) covers name cleaning, the latest-status rule, and that the case table has no column that could hold a defendant's name.

## Caveats

- **One county, one kind of court.** Larger debt suits in county and district courts aren't here.
- **Court pace shapes the outcome shares.** A plaintiff that files mostly in slower courts shows fewer default judgments so far. Compare plaintiffs with that in mind, or within one court.
- **"Dropped by plaintiff" has no reason attached.** The records don't say whether a case was settled, paid, or abandoned.
- **The attorney field** records an attorney of record. Advice or limited help that never appears on the docket isn't in it. What else the field includes or misses is **not confirmed**.
- **2026 is incomplete,** and November 2026 covers ten days.

## Next steps

_Noted 2026-11-12. In rough order._

1. **Check the daily job's first runs.** _Runs checked 2026-11-13: both scheduled runs (11-12, 11-13) succeeded and wrote a snapshot under `raw/harris/debt_claims_filed/`._ Still to do: subscribe an email address to the alerts topic ([`docs/aws-setup.md`](../aws-setup.md), Step 9); the read-only user can't see whether that's done.
2. **Test the Athena table.** _Partly done 2026-11-13: `harris_debt_claims_raw` returns both partitions, with row counts matching the job's log lines (5,121 and 4,982)._ The saved query `harris-cases-latest` hasn't been run yet. Cloud sessions need `AWS_DEFAULT_REGION=us-east-2` (boto3 ignores `AWS_REGION`) and `boto3` (`uv run --with boto3`).
   **Then set the window length:** cases reach the extract late ([late-entries.md](late-entries.md)). After about two weeks of snapshots, rerun that comparison and set `WINDOW_DAYS` so it catches nearly all late entries.
3. **Load the history into the raw bucket.** Invoke the function once per month of filings, 2025-01 onward (`{"from": "2025-01-01", "to": "2025-01-31"}`), with a pause between calls. Needs someone who can invoke the function; the read-only user can't.
4. **Build these tables on AWS.** Move the queries in `scripts/docket.py` to Athena (or a scheduled job writing to the curated bucket), with `plaintiff_names.csv` as a small lookup table, so the page rebuilds from the bucket and not from a local download.
5. **Refresh older cases.** The daily job re-reads only the last 14 days of filings, so outcomes that arrive months later are missed. Add a slower job that re-pulls each past month on a rotation.
6. **Weekly alert (PRD R16).** Compare each large plaintiff's filings with its own recent weeks and publish to the alerts topic when one moves well outside them. Thresholds in the repo.
7. **Review the lookup.** Read `plaintiff_names.csv`, especially the kinds, and check the debt-buyer grouping against a source (a state registry or the companies' own filings).
8. **Ask what the attorney field means.** Whether it includes limited-scope appearances and debt-settlement firms is not confirmed. The county clerk's office or a local legal aid program would know.
9. **Compare within a court.** Outcome shares by plaintiff are shaped by court pace. A plaintiff-by-court table would separate the two.
10. **Decide the project's framing.** The README still leads with the legal aid gap. If the docket is the main track, the title, summary and PRD goals should say so.
11. **Fix the county rates on the map,** if the map stays: use Census annual population estimates for the filing year, and say where Hidalgo County is missing ([docs/lawsuits](../lawsuits/README.md)).
12. **A second place.** Virginia may publish case-level General District Court data with attorney fields: not confirmed. It would show whether the Harris County patterns hold elsewhere.

## Reproduce

```bash
# one month per request; the county's server times out on long ranges
uv run python scripts/lawsuits_fetch_harris.py --from 2025-01-01 --to 2025-01-31   # ...and each month after
uv run python scripts/docket.py --data data/harris --out docs/docket
uv run python scripts/docket_page.py
```

On AWS, the daily job writes the same extract to the raw bucket, and the Glue table `harris_debt_claims_raw` makes it queryable in Athena ([`infra/main/harris_table.tf`](../../infra/main/harris_table.tf)). The tables here are built locally for now.
