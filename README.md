# Justice Gap Map

Where is consumer-debt harm high and civil legal aid thin?

This project joins public data from the CFPB Consumer Complaint Database (debt collection), the Legal Services Corporation (legal aid funding and caseloads), and the Census ACS (who's eligible for legal aid) into one map.

Status: **Phase 0**, checking whether the data supports the question. See [docs/prd.md](docs/prd.md) for the plan.

## Setup

```bash
uv sync
export CENSUS_API_KEY=...   # https://api.census.gov/data/key_signup.html
export HUD_API_TOKEN=...    # https://www.huduser.gov/portal/dataset/uspszip-api.html
```

Downloaded data goes in `data/`, which is gitignored.

## License

Code: MIT. Data belongs to its sources: CFPB, LSC, U.S. Census Bureau, HUD.
