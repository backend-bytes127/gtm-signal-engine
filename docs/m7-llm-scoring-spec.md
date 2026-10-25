# M7 — LLM-Powered Signal Scoring

## Status: Proposed

## Problem

The current scoring engine uses hand-tuned heuristics: weighted signals, time decay, and pattern multipliers defined in CSV seed files. This works for known patterns but has three limitations:

1. **Rigid combinations** — the engine can't reason about novel signal patterns it wasn't configured for
2. **Template explanations** — "Why Now" text is assembled from templates, not genuine reasoning about the account's situation
3. **No learning** — weights don't adapt based on which alerts reps actually act on

## Proposed Solution

Replace the heuristic scoring layer with model judgment, using the existing heuristic scores as a pre-filter to control cost and latency.

**Recommended backend: Jev (TypeSafe System One) for the score, Claude only for the prose.** See [Scoring Backend: Jev vs. Claude](#scoring-backend-jev-vs-claude). The Claude-only design further down stays as the alternative.

## Scoring Backend: Jev vs. Claude

[Jev](https://docs.typesafe.ai/api) (`jev-latest`, `POST https://api.typesafe.ai/v1/systemone`) is a judgment API. You send it a `state` object and a set of typed questions, and it returns typed answers: `choice` (one label, with a probability for every option and a confidence), `noul` (a yes/no probability) or `score` (a position on levels you define, with probabilities and a confidence). The questions in one request run in parallel. Our FDE-app project already uses it in production (`src/lib/ingest/jev.ts`, `post-judge.ts`). That project follows the pattern this spec adopts: **code owns the workflow, Jev supplies typed judgments, the raw judgments are stored, and code applies the thresholds.**

### Why Jev for the score

| | Jev | Claude (free-form JSON) |
|---|---|---|
| Output | Typed answers with a probability for every option | Text that has to be parsed and validated |
| Calibration | Probabilities and confidence come back natively | A number the model chooses; it can drift between runs |
| Retuning | Change the tier thresholds in code over stored probabilities, with no re-scoring | Re-prompt and re-score |
| Explanations | None (it returns no prose) | Strong |

### Questions per account (one Jev request)

`state` = the serialized `AccountContext` (see Technical Design §1).

```ts
{
  intent_tier: {
    type: "choice",
    instructions: "How ready is the account in `state` to buy right now?",
    criteria: {
      hot:  { what: "Active evaluation now: several high-intent signals (pricing, demo, competitor research) from multiple people in the last 14 days." },
      warm: { what: "Clear interest but early: some high-intent activity, or broad low-intent activity that is accelerating." },
      cold: { what: "Background noise: sporadic, low-intent or stale activity." },
    },
  },
  buying_committee: {
    type: "noul",
    instructions: "Are multiple stakeholders from this account evaluating together?",
    criteria: {
      true:  "Two or more people, at least one of them senior, show related high-intent activity.",
      false: "Activity comes from one person, or from unrelated people with no shared intent.",
    },
  },
  urgency: {
    type: "score",
    instructions: "How time-sensitive is reaching out to this account?",
    criteria: [
      "No urgency: activity is flat or declining.",
      "Mild: steady interest with no trigger.",
      "High: a recent spike or a trigger event (new leader, funding, competitor evaluation).",
      "Immediate: a hand-raise or a very sharp spike in the last few days.",
    ],
  },
}
```

### How the score is built

- `timing_score` = `P(hot)×100 + P(warm)×60 + P(cold)×10`, adjusted by `urgency` and `buying_committee`. The weights live in a seed CSV, as they do today.
- `tier` comes from code thresholds on `P(hot)` and `confidence`, not from Jev's top label directly. This mirrors `decideKind` in FDE-app.
- Raw probabilities are stored in `llm_account_scores` with the `signal_hash`, so a threshold change needs no API calls.

### Explanations

Jev returns no prose. Two options:
1. **Template (default):** build "Why Now" from the top probabilities and the account's top signals. Free and deterministic.
2. **Claude Haiku for hot accounts only:** pass Jev's judgments plus the context and ask for a 1–2 sentence explanation. That's about 5–20 calls a day.

### Open items for Jev

- Pricing per request: check TypeSafe pricing before finalizing the cost estimate below. The Claude figures there don't apply to Jev.
- Latency: FDE-app's `scripts/jev-sample.ts` logs per-call milliseconds. Run the same sample against 10 accounts.
- Client: port `askJev` (retry on 429/529/5xx with exponential backoff, 30-second timeout) to Python using `httpx` and Pydantic.
- Env var: `TYPESAFE_API_KEY`.

---

## Alternative: Claude as the Scoring Engine

The rest of this spec describes the Claude-only design. If Jev is adopted, §2–3 of the Technical Design (prompt and engine) are replaced by the Jev questions above. Everything else (context assembly, storage, Dagster, activation, dashboard, validation) stays the same.

### Architecture

```
┌─────────────────────────────────────────────────────────┐
│  Existing Pipeline (unchanged)                          │
│                                                         │
│  datagen → bronze → silver → gold (heuristic scores)    │
└──────────────────────┬──────────────────────────────────┘
                       │
                       ▼
┌─────────────────────────────────────────────────────────┐
│  NEW: LLM Scoring Layer                                 │
│                                                         │
│  1. Pre-filter: heuristic score > threshold (~50)       │
│     → narrows 500 accounts to ~50 candidates            │
│                                                         │
│  2. Context assembly: for each candidate, build a       │
│     structured prompt with all signals, contacts,       │
│     event timeline, ICP fit, and historical patterns    │
│                                                         │
│  3. Claude scoring:                                     │
│     - Haiku for bulk candidates (cheap, fast)           │
│     - Sonnet for top 20 by heuristic score (deeper)     │
│                                                         │
│  4. Store LLM score (0-100), tier, and explanation      │
│     back into DuckDB as llm_account_scores              │
│                                                         │
│  5. Activation layer reads llm_account_scores           │
│     instead of heuristic account_scores                 │
└─────────────────────────────────────────────────────────┘
```

### What Changes

| Component | Before (M1-M6) | After (M7) |
|-----------|----------------|------------|
| Scoring engine | Heuristic (CSV weights + multipliers) | Claude LLM with heuristic pre-filter |
| Explanations | Template-assembled strings | Claude-written natural language reasoning |
| Score source | `account_scores` dbt model | `llm_account_scores` table in DuckDB |
| Cost per run | $0 (local compute) | ~$0.50–2.00 (API calls) |
| Latency | Milliseconds | ~30–60 seconds for full batch |
| Adaptability | Manual CSV edits | Prompt engineering + feedback context |

### What Stays the Same

- Data generation (datagen)
- Bronze/silver dbt models
- Gold heuristic models (become the pre-filter)
- Activation layer (HubSpot, Attio, Slack) — reads from new table, same AlertPayload format
- Dashboard — reads from new table, same schema
- Dagster orchestration — new asset added to the DAG
- All existing tests

## Technical Design

### 1. Context Assembly (`scoring/context.py`)

For each candidate account, assemble a structured context object:

```python
@dataclass(frozen=True)
class AccountContext:
    account_id: str
    company_name: str
    domain: str
    icp_fit_score: int          # 1-4
    industry: str
    employee_count: int
    heuristic_score: float      # from existing gold layer
    
    contacts: list[ContactSummary]       # name, title, seniority
    events: list[EventSummary]           # type, timestamp, contact
    pattern_metrics: PatternMetrics      # breadth, channel_mix, spike
    signal_timeline: str                 # human-readable timeline
```

Query DuckDB to hydrate each field from existing silver/gold tables.

### 2. Prompt Design (`scoring/prompts.py`)

System prompt defines the scoring framework:

```
You are a signal scoring engine for enterprise B2B sales.

Given an account's activity signals, contacts, and ICP fit, you must:
1. Score the account 0-100 on buying intent RIGHT NOW (timing score)
2. Assign a tier: hot (80+), warm (50-79), or cold (<50)
3. Write a 1-2 sentence "Why Now" explanation a sales rep can act on

Scoring criteria:
- Multiple people from the same account = stronger signal
- Recent activity > old activity
- High-intent signals (pricing page, demo request, competitive research) > low-intent (blog, social)
- Breadth across channels (web + email + ads) > single channel
- Acceleration (sudden spike vs. baseline) = urgency indicator
- ICP fit amplifies timing — a great-fit account with moderate signals outranks a poor-fit account with strong signals

Respond in JSON:
{
  "score": <0-100>,
  "tier": "hot" | "warm" | "cold",
  "explanation": "<why now, for the rep>",
  "key_signals": ["<top 3 signals driving the score>"],
  "confidence": "high" | "medium" | "low"
}
```

User prompt contains the serialized `AccountContext`.

### 3. LLM Scoring Engine (`scoring/engine.py`)

```python
async def score_accounts(
    candidates: list[AccountContext],
    model_strategy: ModelStrategy = DEFAULT_STRATEGY,
) -> list[LLMScore]:
    """Score candidate accounts using Claude.
    
    Uses tiered model selection:
    - Top N by heuristic score → Sonnet (deeper reasoning)
    - Remaining candidates → Haiku (cost-efficient)
    
    Returns immutable LLMScore objects.
    """
```

Key design decisions:
- **Async with concurrency limit** — score 10 accounts in parallel, respect rate limits
- **Tiered model selection** — configurable threshold for Sonnet vs Haiku
- **Structured output** — parse JSON response into frozen dataclass
- **Fallback** — if Claude call fails, fall back to heuristic score with a flag
- **Caching** — skip re-scoring accounts whose signals haven't changed since last run

### 4. Model Strategy (`scoring/config.py`)

```python
@dataclass(frozen=True)
class ModelStrategy:
    bulk_model: str = "claude-haiku-5-5"
    deep_model: str = "claude-sonnet-5-5"
    deep_threshold_rank: int = 20       # top N get deep model
    heuristic_cutoff: float = 50.0      # min heuristic score to send to LLM
    max_concurrency: int = 10
    temperature: float = 0.0            # deterministic scoring
    max_tokens: int = 512
```

Configurable via environment variables:
```bash
LLM_BULK_MODEL=claude-haiku-5-5
LLM_DEEP_MODEL=claude-sonnet-5-5
LLM_DEEP_THRESHOLD=20
LLM_HEURISTIC_CUTOFF=50
```

### 5. Storage (`scoring/store.py`)

New DuckDB table `llm_account_scores`:

```sql
CREATE TABLE llm_account_scores (
    account_id       VARCHAR PRIMARY KEY,
    company_name     VARCHAR NOT NULL,
    domain           VARCHAR NOT NULL,
    llm_score        DOUBLE NOT NULL,
    tier             VARCHAR NOT NULL,       -- hot, warm, cold
    explanation      VARCHAR NOT NULL,
    key_signals      VARCHAR NOT NULL,       -- JSON array
    confidence       VARCHAR NOT NULL,       -- high, medium, low
    model_used       VARCHAR NOT NULL,       -- which Claude model
    heuristic_score  DOUBLE NOT NULL,        -- original score for comparison
    icp_fit_score    INTEGER NOT NULL,
    scored_at        TIMESTAMP NOT NULL,
    signal_hash      VARCHAR NOT NULL        -- for change detection / caching
);
```

### 6. Dagster Integration (`orchestration/`)

New asset `llm_scores` that depends on `account_scores`:

```
synthetic_data → bronze → silver → gold → account_scores
                                              ↓
                                         llm_scores  ← NEW
                                              ↓
                                        deliver_alerts
```

The `deliver_alerts` asset switches from reading `account_scores` to `llm_account_scores`.

### 7. Activation Layer Updates (`activation/runner.py`)

Minimal change — the runner reads from `llm_account_scores` instead of the dbt `alerts` view. The `AlertPayload` dataclass stays the same; the `explanation` field now contains Claude's reasoning instead of a template string.

### 8. Dashboard Updates (`frontend/`)

- "Why Now" explanations are now LLM-generated (richer, more specific)
- Add `confidence` badge (high/medium/low) to alert cards
- Add `key_signals` as bullet points under each alert
- Add a comparison view: heuristic score vs. LLM score scatter plot
- Add model attribution (Haiku vs. Sonnet) as a subtle tag

## Cost Estimate

| Scenario | Accounts scored | Model mix | Est. cost/run |
|----------|----------------|-----------|---------------|
| Daily batch (500 accounts, 50 pass filter) | 50 | 20 Sonnet + 30 Haiku | ~$0.80 |
| Conservative (higher cutoff, 30 pass) | 30 | 10 Sonnet + 20 Haiku | ~$0.40 |
| Full scoring (no pre-filter, all 500) | 500 | 20 Sonnet + 480 Haiku | ~$4.00 |

Based on ~1,500 input tokens and ~200 output tokens per account. Costs decrease as Anthropic reduces pricing.

## Validation Plan

### Correctness
- All 10 planted buyers must still surface as `hot` tier (recall = 100%)
- LLM scores should correlate with heuristic scores (r > 0.7) but not match exactly
- Explanations must reference specific signals from the account's timeline

### Quality
- Side-by-side comparison: LLM explanations vs. template explanations for the same 10 accounts
- Review with a sales rep persona: "Would you act on this alert?"

### Reliability
- Fallback to heuristic scoring when Claude API is unreachable
- Retry with exponential backoff on transient failures
- Signal hash caching prevents redundant API calls

### Testing
- Unit tests: context assembly, prompt formatting, response parsing
- Integration tests: end-to-end scoring of 5 accounts with mocked Claude responses
- Regression test: planted buyer recall after switching to LLM scoring

## Implementation Phases

### Phase A: Scoring Engine (core)
- [ ] `scoring/context.py` — context assembly from DuckDB
- [ ] `scoring/prompts.py` — system + user prompt templates
- [ ] `scoring/engine.py` — async Claude scoring with tiered model selection
- [ ] `scoring/config.py` — model strategy configuration
- [ ] `scoring/store.py` — DuckDB table creation + write
- [ ] Unit tests for each module

### Phase B: Pipeline Integration
- [ ] Dagster `llm_scores` asset
- [ ] Update `deliver_alerts` to read from `llm_account_scores`
- [ ] Update activation runner
- [ ] Integration tests

### Phase C: Dashboard
- [ ] Confidence badges on alert cards
- [ ] Key signals bullet points
- [ ] Heuristic vs. LLM score comparison chart
- [ ] Model attribution tags

### Phase D: Feedback Loop (future)
- [ ] Include rep feedback (accept/dismiss) in scoring prompt as few-shot examples
- [ ] Track LLM score accuracy vs. conversion outcomes
- [ ] Auto-adjust heuristic cutoff based on LLM agreement rate

## Dependencies

- `anthropic` Python SDK (add to pyproject.toml)
- `ANTHROPIC_API_KEY` environment variable
- Existing DuckDB tables from gold layer must be populated

## Open Questions

1. **Should LLM scoring replace or augment heuristic scoring?** Current design: augment (heuristic is pre-filter). Alternative: replace entirely and use Claude for all 500 accounts (~$4/run).

2. **Batch vs. incremental?** Current design: re-score all candidates daily. Alternative: only re-score accounts whose signals changed (signal hash comparison).

3. **Prompt tuning workflow?** Should prompt changes go through the same seed CSV mechanism, or a separate prompt versioning system?

4. **Jev or Claude for the score?** Recommendation: Jev for typed, calibrated judgments, and Claude Haiku only for hot-account explanations. Confirm after a 10-account side-by-side that includes the 10 planted buyers.
