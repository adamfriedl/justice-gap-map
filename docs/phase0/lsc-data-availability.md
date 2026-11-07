# Phase 0: what LSC data is available?

_Run 2026-11-06. Fifth Phase 0 check, and the PRD's riskiest source._

## Verdict

- **Service areas can very likely be rebuilt from counties.** LSC states that general service areas are drawn to cover every county. In the one county-level list I could download, 34 of 36 general service areas are whole states or lists of whole counties. Two (AZ-2 and CA-31) split counties.
- **There is no downloadable boundary file.** LSC's map draws service areas from Mapbox vector tiles on LSC's own account. The layers are `2024_bf_general`, `2019_ag_worker`, `2019_native_am`, and `counties_2020`.
- **The full county list per area is one step away, not yet in hand.** LSC's map reads each area's description, latest awards, and funding and poverty shares from a public JSON endpoint, `api.lscdataease.org/public/lsc/service_areas/{area}/about.json`. That host isn't on this environment's allowlist, and I didn't add it (see "Blocked" below).
- **Funding:** available by state (LSC state profiles, 2026) and per service area for the third of areas up for competition (estimated 2027 grant). Per-area awards for all areas sit in the same `about.json` endpoint.
- **GAR case closures:** available nationally and by state in By the Numbers 2025 (charts, with selected figures in text). By grantee they're in public DataEase Tableau dashboards that can't be downloaded by script. By service area or county: **not confirmed** that they're published at all.

**Unit decision (provisional):** build service areas as sets of counties. Treat AZ-2 and CA-31 style splits as exceptions, either by assigning a split county to the area holding most of its poor population or by merging the two areas, and document each case. If the full county lists can't be obtained, fall back to county for pressure and state for resources (the resource check already works at state level). The go/no-go condition "LSC data can be attached to some geography" is met either way: state now, service areas probably.

## Sources

| Source | Snapshot | Where |
| --- | --- | --- |
| Service-area list (190 areas: code, type, states) | Embedded in lsc.gov's service-area map module, downloaded 2026-11-06 | `https://www.lsc.gov/modules/custom/lsc_serv_areas_map/lsc_serv_areas_map_app/dist/assets/index.js` |
| 2027 Service Areas Subject to Competition | lsc.gov page, downloaded 2026-11-06 (60 areas) | https://www.lsc.gov/grants/basic-field-grant/lsc-service-areas/2027-service-areas-subject-competition |
| State profiles, By the Numbers 2025, DataEase | As in the capacity check | `docs/phase0/lsc-funding-vs-capacity.md` |

Reproduce:

```bash
uv run python scripts/phase0_lsc_areas.py --raw data/lsc/2026-11-06 --out docs/phase0/lsc-data
```

Outputs: [service_areas.csv](lsc-data/service_areas.csv), [competition_2027.csv](lsc-data/competition_2027.csv), [summary.csv](lsc-data/summary.csv).

## What's downloadable

| Need (PRD) | Status | Detail |
| --- | --- | --- |
| Service-area list | **Yes** | 190 areas: 130 Basic Field–General, 33 Agricultural Worker, 27 Native American, each with its state FIPS codes. Some span states (e.g. MSX-2 and MMX-1). |
| Service-area boundaries | **No file** | Mapbox vector tiles only. Their layer names suggest the general areas are a 2024 vintage built on 2020 counties, but that's inferred from names (**not confirmed**). |
| County list per area | **Partly** | The 2027 competition table covers 60 areas, 36 of them general. The rest sit behind `about.json` (`area_description` field). |
| Funding by state | **Yes** | LSC state profiles, "Funding in 2026" (capacity check). |
| Funding by service area | **Partly** | The 2027 competition table gives the estimated grant and poverty population for 36 general areas: $100.3M across 8.79M people in poverty. All areas: `about.json` (`latest_awards`, `funding_pop`, `funding_pct`). |
| Funding by grantee, all sources | **View only** | DataEase "Grantee Funding" Tableau dashboard (capacity check). |
| GAR case closures | **State, national** | By the Numbers 2025: 771,000+ cases closed in 2025, plus state charts (Figure 4.7). DataEase public "GAR Data" dashboards on Tableau. lsc.gov's "GAR data files" link redirects to the general Research & Data page, so no file was found. |
| Native American funding shares | **Yes** | `Percent of total Native American funding by service area.xlsx` on LSC's Box (linked from the map). Not needed for v1. |

## County structure, from the 2027 sample

| Type | Statewide | Whole-county list | Splits a county |
| --- | --- | --- | --- |
| Basic Field–General (36) | 13 | 21 | 2 |
| Agricultural Worker (10) | 9 | 1 | 0 |
| Native American (14) | 2 | 2 | 10 |

The two general-area splits:

- **AZ-2:** Coconino, plus the Navajo and Hopi reservation parts of Apache and Navajo counties.
- **CA-31:** 15 whole counties, plus the northwest portion of Kern and the Gilroy/Morgan Hill area of Santa Clara.

Native American areas are defined by reservations and tribal membership, not counties. They overlap general areas and should stay off a county-based map. Agricultural worker areas are mostly statewide overlays.

This is a sample of one competition year: 36 of 130 general areas, picked by LSC's grant cycle rather than at random. The share of splits across all 130 is **not confirmed**. Virginia's areas mix counties and independent cities (e.g. VA-16 lists "Chesapeake city, Hampton city"). Independent cities are county-equivalents in Census data, so they join fine.

## Blocked, and what's needed

- `api.lscdataease.org`: LSC's public JSON for each service area. One request per area, 190 requests. It would complete the county lists and per-area awards. It's not on the allowlist. Earlier this session the auto-mode safety check blocked a fetch from a newly added LSC asset host (`d29f85wyq8xezh.cloudfront.net`), so I stopped widening network access and left this one for the maintainer to decide.
- Alternatively, email LSC's data team (datateam@lsc.gov) for a service-area-to-county file. The PRD's risk table already suggests asking LSC's data office.

## Implications for the plan

- Unit of analysis: service areas as county sets, pending the full county lists. Fall back to county and state.
- Resources at service-area level could be LSC's award (from `about.json`) plus 990 revenue spread over the area. Revenue isn't placed at the HQ county (capacity check).
- Add a step to Phase 3's LSC ingest: pull `about.json` for every area in the service-area list, store it raw, and parse `area_description` into county FIPS, with a hand-checked exceptions table.
