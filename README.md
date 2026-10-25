# GTM Signal Engine

A signal prioritization engine for enterprise sales. Replaces noisy single-event alerts with account-level intent scoring — fewer alerts, every one worth acting on.

## Problem

Enterprise revenue teams drown in single-event alerts (page visits, job changes, ad clicks). Reps stop reading them and miss real buyers. The root cause: no decision layer between raw activity and the rep.

## Solution

A scoring engine that judges **patterns, not events**:
- Weights each signal by type and importance
- Decays signals over time (yesterday's pricing visit > last month's)
- Rewards combinations across people and channels (breadth, channel mix, acceleration)
- Alerts only on accounts that cross a threshold
- Attaches a plain-English reason to every alert

## Architecture

![Pipeline Architecture](docs/pipeline_architecture.png)

> *Generated with the [diagrams](https://diagrams.mingrammer.com/) Python library — `python docs/generate_diagram.py` to regenerate.*

📄 **[Full Architecture Spec](docs/architecture.md)** — Functional requirements, data design (ERD + schemas), interface contracts, scoring algorithm, trade-offs, and milestones.

## Stack

| Layer | Tool | Why |
|-------|------|-----|
| Database | DuckDB | Zero-setup, embedded analytical DB, SQL-native |
| Transforms | dbt-core + dbt-duckdb | Medallion models, weights in seed files |
| Orchestration | Dagster | Asset-based DAG, dbt integration, web UI |
| Data generation | Python + Faker | Synthetic accounts, events, planted buyers |
| Activation | HubSpot sandbox | Score + tier + reason as account properties |
| Notifications | Slack | Daily top-accounts summary |
| CI | GitHub Actions | Lint, test, deploy |

## Scoring Model

Three layers:

1. **Weighted signals** — each event type has a base weight
2. **Time decay** — `score = Σ(weight × 2^(-age / half_life))`
3. **Pattern multipliers** — breadth (multiple people), channel mix, acceleration, combo bonuses

```
final_score = base × m_breadth × m_channels × m_spike + combo_bonuses
```

All weights and multipliers live in dbt seed files — tuning is a config change, not a code change.

## Milestones

- [x] **M1 — Data Generation + Scoring Pipeline**
  Faker script (500 accounts, 4.5k contacts, 100k events, 10 planted buyers), full dbt pipeline: bronze staging → silver enrichment → gold scoring (time-decayed weights, pattern multipliers, combo bonuses, ICP fit gate, suppression, attention budget). All 10 planted buyers surface in hot tier.
- [x] **M2 — Dagster Orchestration**
  22 Dagster assets (datagen + 5 seeds + 3 sources + 13 dbt models), daily 6AM UTC schedule, `dagster dev` web UI for observability. Architecture diagram generated with `diagrams` library.
- [ ] **M3 — Activation Layer**
  HubSpot integration (push alerts as tasks/deals), Slack notifications (weekly digest + real-time hot alerts), alert feedback loop.
- [ ] **M4 — Feedback & Tuning**
  Alert feedback table (accept/dismiss/convert), weight auto-tuning from feedback signals, signal effectiveness dashboard.
- [ ] **M5 — Production Hardening**
  Cloud warehouse migration, CI/CD pipeline, dbt tests, data quality checks, auth, rate limiting, monitoring.

## Project Structure

```
gtm-signal-engine/
├── README.md
├── pyproject.toml
├── docs/
│   ├── architecture.md       # Full spec (FR, NFR, data design, HLD, LLD)
│   └── architecture.png      # System diagram
├── datagen/                  # Faker-based synthetic data
│   ├── __main__.py           # Runner — generates all data into DuckDB
│   ├── accounts.py           # Company generation (ICP, competitors, partners)
│   ├── people.py             # Contact generation (seniority distribution)
│   ├── events.py             # Event generation (noise + planted buyers)
│   └── config.py             # Generation parameters (frozen dataclass)
├── dbt_project/              # dbt models (DuckDB adapter)
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── seeds/                # Signal weights, multipliers, exclusions
│   │   ├── signal_taxonomy.csv
│   │   ├── pattern_multipliers.csv
│   │   ├── combo_bonuses.csv
│   │   ├── exclusion_rules.csv
│   │   └── suppression_config.csv
│   └── models/
│       ├── bronze/           # Staging views (stg_accounts, stg_contacts, stg_raw_events)
│       ├── silver/           # cleaned_events (joined, enriched, filtered)
│       └── gold/             # Scoring + activation (9 models)
├── data/                     # Generated at runtime (gitignored)
│   ├── signal_engine.duckdb
│   └── planted_buyer_ids.json
├── orchestration/            # (M2) Dagster definitions
├── activation/               # (M3) HubSpot + Slack push
└── tests/                    # (M2) Test suite
```

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install faker duckdb dbt-core dbt-duckdb dagster dagster-dbt dagster-duckdb dagster-webserver python-dotenv diagrams

# Option 1: Run pipeline manually
python -m datagen
cd dbt_project && dbt seed --profiles-dir . && dbt run --profiles-dir .

# Option 2: Run via Dagster (orchestrated)
DAGSTER_HOME=. dagster dev -m orchestration.definitions
# Then open http://localhost:3000 and materialize all assets
```

## Key Design Decisions

- **Batch over streaming.** Enterprise intent builds over days — daily batch loses nothing. Streaming only for hand-raises.
- **Fit vs Timing as separate axes.** Fit (ICP) doesn't decay. Timing does. Prevents noisy bad-fit accounts from outscoring quiet great-fit ones.
- **Attention budget.** Hard daily cap per AE. New alert in → weakest alert out.
- **Weights in config.** All tuning happens in CSV seed files, not code.
