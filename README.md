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
- Pushes alerts to HubSpot, Attio, and Slack

## Architecture

![Pipeline Architecture](docs/pipeline_architecture.png)

📄 **[Full Architecture Spec](docs/architecture.md)** — Functional requirements, data design (ERD + schemas), interface contracts, scoring algorithm, trade-offs, and milestones.

### Data Flow

```
Raw Events (100K+) → Bronze (staging views) → Silver (cleaned, account-matched)
→ Gold (scored: time-decay × pattern multipliers + combo bonuses)
→ Alerts (top N per attention budget) → CRM + Slack + Dashboard
```

## Stack

| Layer | Tool | Why |
|-------|------|-----|
| Database | DuckDB | Zero-setup, embedded analytical DB, SQL-native |
| Transforms | dbt-core + dbt-duckdb | Medallion models, weights in seed files |
| Orchestration | Dagster | Asset-based DAG, dbt integration, web UI |
| Data generation | Python + Faker | Synthetic accounts, events, planted buyers |
| Frontend | Next.js + React + Recharts | Real-time dashboard with tier charts and alert feed |
| UI Components | shadcn/ui + Tailwind CSS | Enterprise-grade component library |
| Activation | HubSpot + Attio + Slack | Multi-CRM push with dry-run mode |
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

## Frontend Dashboard

The Next.js dashboard provides four views:

- **Dashboard** — KPI cards (accounts, alerts, timing score, planted buyer recall), tier distribution pie chart, top alerts bar chart, recent alerts feed
- **Accounts** — Sortable/filterable account table with tier badges, search, score progress bars
- **Alerts** — Alert cards with "Why Now" explanations, timing + fit scores, accept/dismiss actions
- **Signals** — Event volume bar chart by signal type, signal taxonomy table with weights

The frontend queries DuckDB via Python subprocess to avoid Node.js/Python DuckDB version conflicts.

## Milestones

- [x] **M1 — Data Generation + Scoring Pipeline**
  Faker script (500 accounts, 4.5k contacts, 100k events, 10 planted buyers), full dbt pipeline: bronze staging → silver enrichment → gold scoring (time-decayed weights, pattern multipliers, combo bonuses, ICP fit gate, suppression, attention budget). All 10 planted buyers surface in hot tier.
- [x] **M2 — Dagster Orchestration**
  22 Dagster assets (datagen + 5 seeds + 3 sources + 13 dbt models), daily 6AM UTC schedule, `dagster dev` web UI for observability. Architecture diagram generated with `diagrams` library.
- [x] **M3 — Activation Layer**
  HubSpot + Attio CRM push (company properties + tasks/notes), Slack notifications (daily digest + per-account hot alerts), alert feedback table (accept/dismiss/convert/stale). Dry-run mode when no credentials set.
- [x] **M4 — Feedback & Tuning**
  Alert feedback table (accept/dismiss/convert/stale), signal effectiveness report with per-signal acceptance rates, automated weight tuning recommendations with `--apply` to update seed CSVs.
- [x] **M5 — Production Hardening**
  35 dbt data tests (not_null, unique, accepted_values), 15 Python tests (datagen + scoring validation), GitHub Actions CI (lint + test), planted buyer recall validation.
- [x] **M6 — Frontend Dashboard**
  Next.js 16 + React + shadcn/ui + Recharts. Four pages: Dashboard, Accounts, Alerts, Signals. API routes query DuckDB via Python subprocess. Tier distribution charts, score comparisons, "Why Now" explanations.

## Project Structure

```
gtm-signal-engine/
├── README.md
├── pyproject.toml
├── docs/
│   ├── architecture.md       # Full spec (FR, NFR, data design, HLD, LLD)
│   └── pipeline_architecture.png
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
│   └── models/
│       ├── bronze/           # Staging views
│       ├── silver/           # Cleaned + enriched events
│       └── gold/             # Scoring + activation (9 models)
├── frontend/                 # Next.js dashboard
│   ├── src/
│   │   ├── app/              # Pages (dashboard, accounts, alerts, signals)
│   │   ├── components/       # UI components (sidebar, charts, badges)
│   │   └── lib/              # DB query helper, types
│   ├── package.json
│   └── next.config.ts
├── orchestration/            # Dagster definitions
├── activation/               # CRM + Slack push
│   ├── hubspot.py            # HubSpot company properties + tasks
│   ├── attio.py              # Attio company notes
│   ├── slack.py              # Slack daily digest + hot alerts
│   └── runner.py             # CLI entry point
├── tests/                    # pytest suite (15 tests)
└── data/                     # Generated at runtime (gitignored)
```

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -e ".[dev]"

# Generate data + run pipeline
python -m datagen
cd dbt_project && dbt seed && dbt run && dbt test

# Run tests
PYTHONPATH=. pytest tests/ -v

# Start the dashboard
cd frontend && npm install && npm run dev
# Open http://localhost:3001

# Run activation (dry-run without credentials)
PYTHONPATH=. python -m activation.runner

# Optional: Dagster orchestration UI
DAGSTER_HOME=. dagster dev -m orchestration.definitions
```

### CRM Credentials (Optional)

```bash
# HubSpot
export HUBSPOT_ACCESS_TOKEN=your-token

# Attio
export ATTIO_API_KEY=your-api-key

# Slack
export SLACK_BOT_TOKEN=xoxb-your-token
export SLACK_CHANNEL_ID=C0123456789
```

Without credentials, the activation layer runs in **dry-run mode** — logs what would be pushed without making API calls.

## Key Design Decisions

- **Batch over streaming.** Enterprise intent builds over days — daily batch loses nothing. Streaming only for hand-raises.
- **Fit vs Timing as separate axes.** Fit (ICP) doesn't decay. Timing does. Prevents noisy bad-fit accounts from outscoring quiet great-fit ones.
- **Attention budget.** Hard daily cap per AE. New alert in → weakest alert out.
- **Weights in config.** All tuning happens in CSV seed files, not code.
- **Python subprocess for DuckDB.** Frontend queries go through Python to avoid Node.js/Python DuckDB version conflicts.
- **Multi-CRM activation.** Same alert payload pushes to HubSpot (company properties + tasks) and Attio (company notes) simultaneously.
