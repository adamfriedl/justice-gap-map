#!/usr/bin/env bash
# Phase 0 downloads: the full CFPB complaints CSV and the HUD ZIP->county crosswalk.
# Everything lands under data/ (gitignored). Usage:
#   scripts/phase0_download.sh [HUD_YEAR] [HUD_QUARTER]
# Default HUD quarter is 2026 Q2, the latest published as of 2026-11-06.
set -euo pipefail

cd "$(dirname "$0")/.."
snap=$(date -u +%F)
hud_year=${1:-2026}
hud_q=${2:-2}

# CFPB: one zip, ~360 MB, unzips to ~5.7 GB.
mkdir -p "data/cfpb/$snap"
curl -sSf -o "data/cfpb/$snap/complaints.csv.zip" https://files.consumerfinance.gov/ccdb/complaints.csv.zip
unzip -o -q "data/cfpb/$snap/complaints.csv.zip" -d "data/cfpb/$snap"

# HUD: type=2 is ZIP->county. Needs a registered token.
if [[ -z "${HUD_API_TOKEN:-}" ]]; then
  echo "HUD_API_TOKEN is not set; skipping the HUD crosswalk." >&2
  exit 1
fi
mkdir -p data/hud
curl -sSf -H "Authorization: Bearer $HUD_API_TOKEN" \
  "https://www.huduser.gov/hudapi/public/usps?type=2&query=All&year=$hud_year&quarter=$hud_q" \
  -o "data/hud/zip_county_${hud_year}${hud_q}.json"

echo "CFPB snapshot: data/cfpb/$snap  HUD: data/hud/zip_county_${hud_year}${hud_q}.json"
