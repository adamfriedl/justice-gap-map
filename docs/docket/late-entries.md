# Late entries in the Harris County extract

_Checked 2026-11-13 against the daily job's first two snapshots
(`downloaded=2026-11-12` and `downloaded=2026-11-13` in `harris_debt_claims_raw`)._

**Finding:** cases appear in the county's "cases filed" extract days after
their filing date. A pull the next morning held about half of the previous
day's filings, and cases filed 11 days earlier were still being added. This
is why the daily job's windows overlap (`src/ingest_harris.py`). Without the
overlap, every day's count would come up short, most of all for recent days.

| Filed | Cases in 11-12 pull | Cases in 11-13 pull | New in 11-13 pull |
|---|---|---|---|
| 10/30/2026 | 621 | 621 | 0 |
| 11/02/2026 | 1,644 | 1,653 | 9 |
| 11/03/2026 | 440 | 475 | 35 |
| 11/04/2026 | 308 | 318 | 10 |
| 11/05/2026 | 302 | 302 | 0 |
| 11/06/2026 | 401 | 401 | 0 |
| 11/09/2026 | 465 | 465 | 0 |
| 11/10/2026 | 278 | 285 | 7 |
| 11/11/2026 | 174 | 360 | 186 |
| 11/12/2026 | (outside window) | 102 | 102 |

No case in the 11-12 pull was missing from the 11-13 pull (10/29 fell out of
the window). Counts are distinct case numbers.

The overlap barely records changes to cases already present. Of the 4,633
cases in both pulls, 0 changed status, disposition or judgment date, and 7
changed next hearing date. Outcomes arrive months after filing, beyond any
window the daily job can request (31 days at most); see "Refresh older cases"
in the [docket README](README.md).

**Not yet known:** how long late entries keep arriving. This is one pair of
snapshots a day apart. Once about two weeks of snapshots exist, rerun the query
below on more pairs and set `WINDOW_DAYS` to cover nearly all late entries.

## Query

Athena, workgroup `justice-gap-map`, database `justice_gap_map`:

```sql
with s as (
  select distinct downloaded d, case_number cn, case_file_date fd
  from harris_debt_claims_raw
),
a as (select * from s where d = '2026-11-12'),
b as (select * from s where d = '2026-11-13')
select coalesce(a.fd, b.fd) as filed,
       count(distinct a.cn) as in_first,
       count(distinct b.cn) as in_second,
       count(distinct case when a.cn is null then b.cn end) as only_second,
       count(distinct case when b.cn is null then a.cn end) as only_first
from a full join b on a.cn = b.cn
group by 1 order by 1;
```

The field-change counts come from joining `a` and `b` on case number and
counting cases where `case_status`, `next_hearing_date`, `disposition_desc` or
`judgment_date` differ.
