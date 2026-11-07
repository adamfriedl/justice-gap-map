# Phase 0: what LSC data is available?

_First run 2026-11-06 (partial). Finished 2026-11-07, once `api.lscdataease.org` was allowlisted. Fifth Phase 0 check, and the PRD's riskiest source._

## Verdict: pass

- **Service areas can be rebuilt from counties.** LSC publishes a description for each of its 130 Basic Field–General service areas. Parsed and matched to Census county FIPS codes, they cover **every county-equivalent in the 50 states, DC, and Puerto Rico**. 3,214 counties belong to exactly one area, and 8 split counties are shared by 2 or 3 areas.
- **The splits are few and contained.** 13 of the 130 areas split a county, and together they hold 11.5% of the eligible population. Merging areas that share a county gives **122 analysis units**, with each county in exactly one. Only five units are merges: Arizona's Navajo/Hopi pair, two California clusters (Los Angeles; Kern and Santa Clara), greater Boston, and Puerto Rico.
- **Funding by service area: yes.** The same source gives each area's FY2025 LSC award ($481.2M across the 130 general areas), its current grantee, and its eligible population.
- **GAR case closures:** state and national only (By the Numbers 2025, DataEase Tableau dashboards). No service-area or county figures found (**not confirmed** that they exist publicly).
- **Boundary file:** LSC's grantee map loads one (`LSC_basic_field_service_areas_08_17_2026.json`) through an AWS API Gateway. I didn't download it; see "Not fetched" below. The county sets make it unnecessary for v1.

**Unit decision:** use the 122 analysis units, built as county sets, as the unit of analysis. Attach pressure measures (debt in collections, complaints) by county, and LSC awards by area. The go/no-go condition "LSC data can be attached to some geography" is met.

## Sources

| Source | Snapshot | Where |
| --- | --- | --- |
| Service-area list (190 areas: code, type, states) | lsc.gov service-area map module, 2026-11-06 | `https://www.lsc.gov/modules/custom/lsc_serv_areas_map/lsc_serv_areas_map_app/dist/assets/index.js` |
| Service-area details (description, delineation codes, current grantee, latest award, eligible population) | One JSON per area, downloaded 2026-11-07. Each file carries `last_updated` (CA-31: 2026-04-22). Awards are FY2025 for all 130 general areas. | `https://api.lscdataease.org/public/lsc/service_areas/{area}/about.json`, the source behind lsc.gov's service-area map |
| 2027 Service Areas Subject to Competition | lsc.gov, 2026-11-06 | https://www.lsc.gov/grants/basic-field-grant/lsc-service-areas/2027-service-areas-subject-competition |
| County names and FIPS | ACS 2020–2024 5-year county list | Census API (same file as the earlier checks) |

Reproduce:

```bash
uv run python scripts/phase0_lsc_areas.py --raw data/lsc/2026-11-06 --out docs/phase0/lsc-data
uv run python scripts/phase0_lsc_about.py --areas docs/phase0/lsc-data/service_areas.csv \
    --acs data/acs/county_acs5_2024.json --raw data/lsc/2026-11-07/about --out docs/phase0/lsc-data
```

Outputs in [`lsc-data/`](lsc-data/):

- [service_areas_about.csv](lsc-data/service_areas_about.csv): one row per area (all 190), with grantee, award, eligible population, structure, and description.
- [area_county.csv](lsc-data/area_county.csv): the general area → county FIPS crosswalk, with a flag for split counties.
- [county_coverage.csv](lsc-data/county_coverage.csv): areas per county.
- [analysis_units.csv](lsc-data/analysis_units.csv): the merged units.
- [unmatched_county_names.csv](lsc-data/unmatched_county_names.csv), plus the earlier [service_areas.csv](lsc-data/service_areas.csv), [competition_2027.csv](lsc-data/competition_2027.csv), and [summary.csv](lsc-data/summary.csv).

## How the areas are built

LSC tags each area with `delineation` codes. Two are explained in LSC's map code:

- **3:** a county is split along minor civil divisions (towns, cities).
- **4:** a county is split along census tracts.

The meanings of 1, 2, and 7 are inferred from the descriptions (**not confirmed**): 1 is statewide, 2 is whole counties, and 7 is Puerto Rico's single exception.

| General areas (130) | Areas | Eligible population |
| --- | --- | --- |
| Statewide | 30 | |
| Lists of whole counties | 87 | |
| Split at least one county | 13 | 6.05M of 52.58M (11.5%) |

LSC's eligible-population figures are from the `demographics.eligible` field.

The 13 splitting areas: AZ-2 and AZ-5 (Navajo and Hopi reservation parts of Apache and Navajo counties), CA-2, CA-19, CA-28, CA-29, CA-30, and CA-31 (Kern, Los Angeles, Santa Clara), MA-4, MA-11, and MA-12 (Middlesex and Norfolk, split by town), and PR-1 and PR-2 (the Hato Rey area of San Juan).

**Parsing notes.** All of these are handled in `scripts/phase0_lsc_about.py` and tested:

- Description wording varies: "counties," "parishes" (Louisiana), "counties and independent cities" (Virginia), "all counties in X except …" (e.g. GA-2, NM-5), "Serves Philadelphia," and VA-19's bare list with no header.
- LSC still lists South Dakota's "Shannon" County, renamed Oglala Lakota in 2015 (FIPS 46102).
- Three names don't match the 2024 county list, and none affects coverage:
  - Bedford city and Clifton Forge city (VA-19) are former independent cities, since merged into Bedford and Alleghany counties, which VA-19 also lists.
  - Guam isn't in the ACS county file.
- In LSC's text, Massachusetts's MA-11 lists Middlesex and Norfolk without saying "part of." Its delineation code (3) and the overlaps with MA-4 and MA-12 show they're split.

**How to use split counties.** The clean option is the 122 merged units. The alternative keeps all 130 areas and allocates a split county's people by LSC's tract or town definitions. That needs the boundary file or LSC's tract lists, and buys little: the merges touch five places, and four of them are a single metro area or reservation.

## Funding and caseload, by geography

| | National | State | Service area | Grantee | County |
| --- | --- | --- | --- | --- | --- |
| LSC award | ✓ | ✓ (state profiles) | ✓ (`about.json`, FY2025) | ✓ (1 grantee per area) | via area |
| All-source revenue | ✓ (By the Numbers) | ✓ (By the Numbers charts; IRS data) | — | Tableau view only | — |
| GAR case closures | ✓ | ✓ (By the Numbers, Tableau) | **not found** | Tableau view only | **not found** |

## Not fetched

- **The boundary GeoJSON.** `serviceAreasMap.js` on LSC's CloudFront loads `LSC_basic_field_service_areas_08_17_2026.json` (and `mapAreasData_keyed.json`) from an AWS API Gateway, `lt2v6wga3l.execute-api.us-east-1.amazonaws.com/default/lsc-data-api?key=lsc-website/our-grantees-map/…`. The `key` is a storage path, not a credential. The same files on CloudFront return 403. I added the gateway host to the allowlist, but the auto-mode safety check denied the download, so it wasn't attempted again. Boundaries aren't needed for the county-set approach. They'd only matter for allocating the 8 split counties by tract. If wanted, the maintainer can download the file in a browser, or allow the fetch.
- **GAR by service area or county.** Ask LSC's data team (datateam@lsc.gov).

## Implications for the plan

- **Unit of analysis:** the 122 analysis units. Store `area_county.csv` and `analysis_units.csv` as versioned crosswalks, as R3 asks. Re-pull `about.json` each year, since areas are re-competed on a three-year cycle and `last_updated` changes.
- **LSC ingest (Phase 3)** can be automated, not a manual drop: 190 small JSON requests a year.
- **Agricultural Worker and Native American areas** overlap the general areas. Keep them off the county map.
- New hosts used this session: `api.lscdataease.org` (needed), `d29f85wyq8xezh.cloudfront.net` (LSC map assets), and `lt2v6wga3l.execute-api.us-east-1.amazonaws.com` (boundary file, not fetched).
