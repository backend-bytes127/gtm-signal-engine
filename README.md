# GTM Signal Engine

> A signal prioritization engine for enterprise sales that replaces noisy single-event alerts with account-level intent scoring — fewer alerts, every one worth acting on.

## The Problem

Enterprise revenue teams drown in single-event alerts — page visits, job changes, ad clicks, webinar signups. Reps get 50+ notifications a day, stop reading them, and miss real buyers hiding in the noise.

**Root cause**: there's no decision layer between raw activity and the rep. Every event gets equal weight, with no context about patterns, timing, or account-level behavior.

## The Solution

A scoring engine that judges **patterns, not events**:

- **Weighted signals** — each event type carries a different base weight (pricing page visit > blog view)
- **Time decay** — yesterday's pricing visit matters more than last month's (`score = weight x 2^(-age / half_life)`)
- **Pattern multipliers** — rewards breadth (multiple people), channel mix, acceleration spikes, and combo bonuses
- **ICP fit gate** — separates timing (decays) from fit (doesn't), preventing noisy bad-fit accounts from outscoring quiet great-fit ones
- **Attention budget** — hard daily cap per AE; new alert in, weakest alert out
- **Plain-English explanations** — every alert tells the rep *why now*
- **Multi-CRM activation** — pushes to HubSpot, Attio, and Slack simultaneously

## In Action

### Dashboard — KPI Cards, Tier Distribution, Top Alerts
![Dashboard](docs/screenshots/dashboard.jpg)

### Slack — Daily Digest
![Slack Digest](docs/screenshots/slack-digest.jpg)

### Slack — Individual Hot Alerts
![Slack Alerts](docs/screenshots/slack-alerts.jpg)

### Attio CRM — Signal Alert Notes
![Attio Notes](docs/screenshots/attio-notes.jpg)

### HubSpot — Companies Created from Alerts
![HubSpot Companies](docs/screenshots/hubspot-companies.jpg)

### Dagster — Asset Lineage (22 Assets across 5 Groups)
![Dagster Lineage Top](docs/screenshots/dagster-lineage-top.jpg)
![Dagster Lineage Bottom](docs/screenshots/dagster-lineage-bottom.jpg)

## Architecture

![Pipeline Architecture](docs/pipeline_architecture.png)

**[Full Architecture Spec](docs/architecture.md)** — Functional requirements, data design (ERD + schemas), interface contracts, scoring algorithm, trade-offs, and milestones.

### Data Flow (Medallion Architecture)

```
Raw Events (100K+)
  → Bronze (staging views — raw ingest)
  → Silver (cleaned, deduplicated, account-matched)
  → Gold (scored: time-decay x pattern multipliers + combo bonuses)
  → Alerts (top N per attention budget, with explanations)
  → Activation (HubSpot + Attio + Slack + Dashboard)
```

## Tech Stack

| Layer | Tool | Why |
|-------|------|-----|
| Database | DuckDB | Zero-setup embedded analytical DB, SQL-native |
| Transforms | dbt-core + dbt-duckdb | Medallion models, weights in seed CSVs |
| Orchestration | Dagster | Asset-based DAG, dbt integration, web UI |
| Data Generation | Python + Faker | Synthetic accounts, events, planted buyers |
| Frontend | Next.js 16 + React + Recharts | Dashboard with tier charts and alert feed |
| UI Components | shadcn/ui + Tailwind CSS | Enterprise-grade component library |
| Activation | HubSpot + Attio + Slack | Multi-CRM push with dry-run mode |
| Testing | pytest + dbt test | 15 Python tests + 35 dbt data tests |
| CI | GitHub Actions | Lint, test, deploy |

## How It Works — Step by Step

For readers unfamiliar with the tools: here's what each layer does and how they connect.

### 1. Data Generation (`python -m datagen`)

A Python script generates realistic synthetic data into **DuckDB** (an embedded SQL database — no server needed):
- **500 companies** with ICP fit scores (1–4)
- **4,500 contacts** across those companies
- **100,000+ events** (page visits, demo requests, job changes, etc.)
- **10 planted buyers** — accounts with deliberate high-intent patterns to validate recall

### 2. dbt Pipeline (`dbt seed && dbt run && dbt test`)

**dbt (data build tool)** transforms raw data through SQL models organized in a medallion architecture:

```
Bronze (raw staging)     → stg_accounts, stg_contacts, stg_raw_events
Silver (cleaned)         → cleaned_events (deduplicated, account-matched)
Gold (scored + alerted)  → int_base_scores → int_pattern_metrics → account_scores → alerts
```

- **Seeds** are CSV config files (signal weights, multipliers, combo bonuses) — edit a CSV to retune, no code changes
- **Tests** (35 total) validate data quality: not-null checks, unique constraints, accepted value ranges
- Run `dbt test` to verify all 35 pass

### 3. Dagster Orchestration (`dagster dev`)

**Dagster** is the scheduler that runs everything in the right order:
- **22 assets** organized into 5 groups: bronze, default (seeds), silver, gold, activation
- **Asset lineage graph** shows dependencies — Dagster knows what to re-run when upstream data changes
- **Daily schedule** at 6 AM UTC — regenerates data, re-runs dbt, delivers alerts
- **Web UI** at `localhost:3002` for monitoring runs, viewing lineage, and triggering manual materializations

### 4. Activation (`python -m activation.runner`)

Reads the scored alerts from DuckDB and pushes them to three channels simultaneously:
- **HubSpot** — creates/updates company records with signal descriptions, creates follow-up tasks
- **Attio** — creates company records with signal alert notes
- **Slack** — posts a daily digest + individual alert cards to `#signal-alerts`

Without API credentials, everything runs in **dry-run mode** — logs exactly what would be sent.

### 5. Dashboard (`npm run dev` in `/frontend`)

A Next.js web app at `localhost:3001` that reads scored data from DuckDB and shows:
- KPI summary cards, tier distribution charts, top alerts with "Why Now" explanations
- Sortable account tables, signal taxonomy breakdowns, accept/dismiss actions

## Scoring Model

Three layers combine to produce a final score per account:

**1. Weighted Signals** — each event type has a configurable base weight (seed CSV)

**2. Time Decay** — recent activity matters more:
```
signal_score = weight x 2^(-age_days / half_life)
```

**3. Pattern Multipliers** — rewards buying behavior patterns:
```
final_score = base x m_breadth x m_channels x m_spike + combo_bonuses
```

| Multiplier | What it rewards |
|-----------|-----------------|
| Breadth | Multiple people from the same account engaged |
| Channel mix | Activity across different signal types |
| Spike | Sudden acceleration vs. historical average |
| Combo bonuses | Specific high-intent signal combinations |

All weights and multipliers live in dbt seed files — **tuning is a config change, not a code change**.

## Frontend Dashboard

Four views built with Next.js 16 + shadcn/ui:

| Page | What it shows |
|------|--------------|
| **Dashboard** | KPI cards (accounts, alerts, timing score, planted buyer recall), tier distribution pie chart, top alerts bar chart, recent alerts feed |
| **Accounts** | Sortable/filterable account table with tier badges, search, score progress bars |
| **Alerts** | Alert cards with "Why Now" explanations, timing + fit scores, accept/dismiss actions |
| **Signals** | Event volume bar chart by signal type, signal taxonomy table with weights |

The frontend queries DuckDB via Python subprocess to avoid Node.js/Python DuckDB version conflicts.

## Activation Layer

The same `AlertPayload` pushes to three channels simultaneously:

| Channel | What gets created | Details |
|---------|-------------------|---------|
| **HubSpot** | Company + Task | Company with signal description, task with tier/score/explanation |
| **Attio** | Company + Note | Company record with two signal alert notes per account |
| **Slack** | Digest + Alerts | Daily digest to `#signal-alerts`, plus individual cards for each hot account |

Without credentials, activation runs in **dry-run mode** — logs what would be pushed without making API calls.

## Milestones

- [x] **M1 — Data Generation + Scoring Pipeline**
  Faker script (500 accounts, 4.5k contacts, 100k events, 10 planted buyers), full dbt pipeline: bronze staging → silver enrichment → gold scoring (time-decayed weights, pattern multipliers, combo bonuses, ICP fit gate, suppression, attention budget). All 10 planted buyers surface in hot tier.

- [x] **M2 — Dagster Orchestration**
  22 Dagster assets (datagen + 5 seeds + 3 sources + 13 dbt models), daily 6 AM UTC schedule, `dagster dev` web UI for observability.

- [x] **M3 — Activation Layer**
  HubSpot + Attio CRM push (company properties + tasks/notes), Slack notifications (daily digest + per-account hot alerts), alert feedback table. Dry-run mode when no credentials set.

- [x] **M4 — Feedback & Tuning**
  Signal effectiveness report with per-signal acceptance rates, automated weight tuning recommendations with `--apply` to update seed CSVs.

- [x] **M5 — Production Hardening**
  35 dbt data tests (not_null, unique, accepted_values), 15 Python tests (datagen + scoring validation), GitHub Actions CI (lint + test), planted buyer recall validation.

- [x] **M6 — Frontend Dashboard**
  Next.js 16 + React + shadcn/ui + Recharts. Four pages with tier distribution charts, score comparisons, and "Why Now" explanations.

- [ ] **M7 — LLM-Powered Signal Scoring** *(proposed — [spec](docs/m7-llm-scoring-spec.md))*
  Claude as the scoring engine: heuristic scores pre-filter ~500 accounts down to ~50 candidates, then Haiku (bulk) and Sonnet (top 20) score intent and write a "Why Now" explanation for each one. Falls back to the heuristic score if the API fails. Estimated cost is about $0.80 per daily run.

## Project Structure

```
gtm-signal-engine/
├── README.md
├── pyproject.toml
├── docs/
│   ├── architecture.md            # Full spec (FR, data design, HLD, LLD)
│   ├── pipeline_architecture.png
│   └── screenshots/               # Live integration screenshots
├── datagen/                       # Faker-based synthetic data
│   ├── __main__.py                # Runner — generates all data into DuckDB
│   ├── accounts.py                # Company generation (ICP scoring)
│   ├── people.py                  # Contact generation (seniority distribution)
│   ├── events.py                  # Event generation (noise + planted buyers)
│   └── config.py                  # Generation parameters (frozen dataclass)
├── dbt_project/                   # dbt models (DuckDB adapter)
│   ├── dbt_project.yml
│   ├── profiles.yml
│   ├── seeds/                     # Signal weights, multipliers, exclusions
│   └── models/
│       ├── bronze/                # Staging views
│       ├── silver/                # Cleaned + enriched events
│       └── gold/                  # Scoring + activation (9 models)
├── frontend/                      # Next.js dashboard
│   ├── src/
│   │   ├── app/                   # Pages (dashboard, accounts, alerts, signals)
│   │   ├── components/            # UI components (sidebar, charts, badges)
│   │   └── lib/                   # DB query helper, types
│   ├── package.json
│   └── next.config.ts
├── orchestration/                 # Dagster asset definitions
├── activation/                    # CRM + Slack push
│   ├── hubspot.py                 # HubSpot company properties + tasks
│   ├── attio.py                   # Attio company notes
│   ├── slack.py                   # Slack daily digest + hot alerts
│   └── runner.py                  # CLI entry point
├── tests/                         # pytest suite (15 tests)
└── data/                          # Generated at runtime (gitignored)
```

## Quick Start

```bash
# Clone and setup
git clone https://github.com/backend-bytes127/gtm-signal-engine.git
cd gtm-signal-engine
python3 -m venv venv && source venv/bin/activate
pip install -e ".[dev]"

# Generate synthetic data + run scoring pipeline
python -m datagen
cd dbt_project && dbt seed && dbt run && dbt test && cd ..

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

Create a `.env` file in the project root:

```bash
# HubSpot
HUBSPOT_ACCESS_TOKEN=your-token

# Attio
ATTIO_API_KEY=your-api-key

# Slack
SLACK_BOT_TOKEN=xoxb-your-token
SLACK_CHANNEL_ID=C0123456789
```

Then source it before running activation:

```bash
set -a && source .env && set +a
PYTHONPATH=. python -m activation.runner
```

## Key Design Decisions

| Decision | Rationale |
|----------|-----------|
| **Batch over streaming** | Enterprise intent builds over days — daily batch loses nothing. Streaming only for hand-raises. |
| **Fit vs Timing as separate axes** | Fit (ICP) doesn't decay. Timing does. Prevents noisy bad-fit accounts from outscoring quiet great-fit ones. |
| **Attention budget** | Hard daily cap per AE. New alert in → weakest alert out. Protects rep focus. |
| **Weights in config** | All tuning happens in CSV seed files, not code. Non-engineers can adjust. |
| **Python subprocess for DuckDB** | Frontend queries go through Python to avoid Node.js/Python DuckDB version conflicts. |
| **Multi-CRM activation** | Same alert payload pushes to HubSpot + Attio + Slack. Swap or add CRMs without changing scoring logic. |
| **Dry-run mode** | No credentials = full pipeline runs with logged output. Zero setup friction for evaluation. |
