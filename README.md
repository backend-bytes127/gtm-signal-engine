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

### End-to-End Flow

```mermaid
flowchart LR
    subgraph SRC["1 · Sources"]
        DG["datagen<br/>500 accounts · 4.5k contacts<br/>100k events · 10 planted buyers"]
    end

    subgraph DB["2 · DuckDB + dbt (medallion)"]
        direction LR
        B[("Bronze<br/>raw staging views")]
        S[("Silver<br/>cleaned, account-matched")]
        G[("Gold<br/>scored + explained")]
        B --> S --> G
    end

    CFG[/"Seed CSVs<br/>weights · multipliers · combos"/]

    subgraph ACT["3 · Activation"]
        HS["HubSpot<br/>company + task"]
        AT["Attio<br/>company + note"]
        SL["Slack<br/>digest + hot alerts"]
    end

    UI["4 · Next.js Dashboard"]
    FB[("Rep feedback<br/>accept · dismiss · convert")]

    DG --> B
    CFG -.-> G
    G -->|alerts| HS & AT & SL
    G --> UI
    UI --> FB
    FB -.->|"tuning report (M4)"| CFG

    DAG{{"Dagster<br/>daily 06:00 UTC"}} -.->|orchestrates| DG & DB & ACT
```

### dbt Model Lineage (Medallion Architecture)

Generated from the actual `ref()` dependencies in `dbt_project/models`:

```mermaid
flowchart LR
    classDef bronze fill:#f3e3d3,stroke:#a0522d,color:#000
    classDef silver fill:#e8e8e8,stroke:#707070,color:#000
    classDef gold fill:#fff3c4,stroke:#b8860b,color:#000
    classDef seed fill:#e3f2fd,stroke:#1e88e5,color:#000

    stg_accounts:::bronze
    stg_contacts:::bronze
    stg_raw_events:::bronze
    signal_taxonomy[/signal_taxonomy/]:::seed
    combo_bonuses[/combo_bonuses/]:::seed
    suppression_config[/suppression_config/]:::seed
    exclusion_rules[/exclusion_rules/]:::seed

    cleaned_events:::silver

    stg_raw_events & stg_contacts & stg_accounts & signal_taxonomy --> cleaned_events

    cleaned_events --> int_base_scores:::gold
    cleaned_events --> int_pattern_metrics:::gold
    cleaned_events & combo_bonuses --> int_combo_matches:::gold
    stg_accounts --> int_fit_scores:::gold

    int_base_scores & int_pattern_metrics & int_combo_matches & int_fit_scores --> account_scores:::gold
    account_scores & int_combo_matches --> score_explanations:::gold
    account_scores & suppression_config & exclusion_rules & stg_accounts --> int_suppression:::gold
    int_suppression & suppression_config --> int_attention_budget:::gold
    int_attention_budget & score_explanations & account_scores --> alerts:::gold
```

| Layer | Models | What happens |
|-------|--------|-------------|
| **Bronze** | `stg_accounts`, `stg_contacts`, `stg_raw_events` | Raw data, typed and renamed. No business logic. |
| **Silver** | `cleaned_events` | Deduplicated, matched to accounts, signal type and weight attached. |
| **Gold** | 9 models ending in `alerts` | Decay, patterns, combos, fit, suppression, attention budget, explanations. |

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

### How One Account Gets Scored

```mermaid
flowchart TD
    E["Account's events"] --> W["× base weight<br/>demo request 10 · pricing 5 · blog 0.5"]
    W --> D["× time decay 2^(−age / half-life)<br/>pricing: 5-day half-life · funding: 90-day"]
    D --> BASE["Base score = Σ"]

    E --> P{"Pattern checks"}
    P -->|"2 people → ×1.3<br/>3+ people → ×1.6"| MB["× breadth"]
    P -->|"2 sources → ×1.2<br/>3+ sources → ×1.4"| MC["× channel mix"]
    P -->|"2× / 4× / 8× the<br/>8-week average"| MS["× spike 1.2 / 1.5 / 1.8"]
    P -->|"e.g. trial + pricing<br/>within 14 days"| CB["Combo bonus: plus 8 to 15 pts"]

    BASE & MB & MC & MS & CB --> T["Timing score 0–100"]

    T --> FIT{"ICP fit gate<br/>fit 1–4, does not decay"}
    FIT --> SUP{"Excluded?<br/>open deal · customer · competitor<br/>partner · do-not-contact · 7-day cooldown"}
    SUP -->|yes| X2["Dropped"]
    SUP -->|no| TIER{"Tier<br/>hot > 70 · warm > 40 · watch > 20"}
    TIER --> BUD{"Within budget?<br/>max 5 alerts per AE per day"}
    BUD -->|no| X3["Held — weakest drops out"]
    BUD -->|yes| AL["🔥 Alert + Why-Now explanation"]
```

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

```mermaid
sequenceDiagram
    autonumber
    participant D as Dagster (06:00 UTC)
    participant R as activation.runner
    participant DB as DuckDB (gold.alerts)
    participant H as HubSpot
    participant A as Attio
    participant S as Slack #signal-alerts

    D->>R: materialize deliver_alerts
    R->>DB: SELECT today's alerts
    DB-->>R: AlertPayload[]
    loop each alert
        R->>H: search company by domain
        alt exists
            R->>H: PATCH description
        else new
            R->>H: POST company
        end
        R->>H: POST task (priority by tier)
        R->>A: query / create company
        R->>A: POST note
    end
    R->>S: daily digest (all hot + warm)
    loop each hot alert
        R->>S: hot-account card
    end
    Note over R: No credentials → dry-run, logs payloads only
```

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

### Roadmap

```mermaid
flowchart LR
    classDef done fill:#d4edda,stroke:#28a745,color:#000
    classDef next fill:#fff3cd,stroke:#e0a800,color:#000
    classDef later fill:#e2e3e5,stroke:#6c757d,color:#000

    subgraph V1["v1 — Built ✅"]
        direction TB
        M1["M1 Data + Scoring"]:::done --> M2["M2 Dagster"]:::done --> M3["M3 Activation"]:::done
        M3 --> M4["M4 Feedback"]:::done --> M5["M5 Hardening"]:::done --> M6["M6 Dashboard"]:::done
    end

    subgraph V2["v2 — Enterprise (proposed)"]
        direction TB
        M7["M7 Jev / LLM Scoring"]:::next
        M8["M8 Real Data Connectors"]:::next
        M9["M9 Production Deployment"]:::next
        M10["M10 Auth, Multi-Tenant, Routing"]:::later
        M11["M11 Closed-Loop Attribution"]:::later
        M8 --> M9 --> M10
        M7 --> M11
        M9 --> M11
    end

    V1 --> V2
```

Full scope, diagrams and acceptance criteria for M8–M11: **[docs/roadmap.md](docs/roadmap.md)**

- [ ] **M7 — LLM-Powered Signal Scoring** *(proposed — [spec](docs/m7-llm-scoring-spec.md))*
  Model judgment replaces the hand-tuned weights. Heuristic scores pre-filter ~500 accounts down to ~50 candidates. Jev (TypeSafe System One) answers typed questions about each one (intent tier, buying committee, urgency) with calibrated probabilities, and code turns those into scores and tiers. Claude Haiku writes "Why Now" explanations for hot accounts. Falls back to the heuristic score if the API fails.

- [ ] **M8 — Real Data Connectors** *(proposed — [roadmap](docs/roadmap.md#m8--real-data-connectors))*
  Replace Faker with live sources: HubSpot/Salesforce activity, website analytics (Segment/GA4), job-change and third-party intent feeds. Each source is a Dagster asset writing to bronze; dbt models unchanged.

- [ ] **M9 — Production Deployment** *(proposed — [roadmap](docs/roadmap.md#m9--production-deployment))*
  DuckDB file → hosted warehouse (MotherDuck or Postgres), Dagster on Dagster+ or a container, dashboard on Vercel, secrets in a manager, CI/CD with preview environments, pipeline alerting.

- [ ] **M10 — Auth, Multi-Tenant & Alert Routing** *(proposed — [roadmap](docs/roadmap.md#m10--auth-multi-tenant--alert-routing))*
  SSO login, role-based access, per-team signal config, territory-based routing so each AE gets only their accounts within their own attention budget.

- [ ] **M11 — Closed-Loop Attribution** *(proposed — [roadmap](docs/roadmap.md#m11--closed-loop-attribution))*
  Pull opportunity and closed-won outcomes back from the CRM, measure alert precision and pipeline influenced, feed outcomes into weight tuning and Jev thresholds.

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
