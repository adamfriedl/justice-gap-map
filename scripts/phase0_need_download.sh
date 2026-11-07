#!/usr/bin/env bash
# Downloads for the Phase 0 "Do complaints measure need?" check. Lands under data/ (gitignored).
#   scripts/phase0_need_download.sh
# Also needs the CFPB CSV and HUD crosswalk from scripts/phase0_download.sh, and the
# Texas court files from scripts/phase0_tx_courts_fetch.py.
set -euo pipefail
cd "$(dirname "$0")/.."

# Urban Institute, Debt in America (credit data August 2025, published 2025-11-20).
# These are the CSVs the interactive map loads. The "Download data" link goes to
# datacatalog.urban.org, which refuses automated requests (HTTP 403 from the site).
urban=data/urban/2025-11-20
mkdir -p "$urban"
for f in county_overall county_medical state_national_overall; do
  curl -sSf -o "$urban/$f.csv" "https://apps.urban.org/features/debt-interactive-map/data/20251023-update/$f.csv"
done
curl -sSf -o "$urban/debt_interactive_technical_appendix_2025.pdf" \
  https://apps.urban.org/features/debt-interactive-map/downloadable-docs/debt_interactive_technical_appendix_2025.pdf

# ACS 2020-2024 5-year, all counties: total population, and the population under
# 125% of poverty (C17002: _002 <0.50, _003 0.50-0.99, _004 1.00-1.24).
if [[ -z "${CENSUS_API_KEY:-}" ]]; then
  echo "CENSUS_API_KEY is not set; skipping ACS." >&2
  exit 1
fi
mkdir -p data/acs
curl -sSf -o data/acs/county_acs5_2024.json \
  "https://api.census.gov/data/2024/acs/acs5?get=NAME,B01003_001E,C17002_001E,C17002_002E,C17002_003E,C17002_004E&for=county:*&key=$CENSUS_API_KEY"
echo "done"
