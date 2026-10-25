"""Tests for scoring pipeline output validation."""
import json
from pathlib import Path

import duckdb
import pytest

DB_PATH = Path(__file__).parent.parent / "data" / "signal_engine.duckdb"
PLANTED_PATH = Path(__file__).parent.parent / "data" / "planted_buyer_ids.json"


@pytest.fixture
def conn():
    if not DB_PATH.exists():
        pytest.skip("DuckDB not found — run `python -m datagen && cd dbt_project && dbt seed && dbt run` first")
    connection = duckdb.connect(str(DB_PATH), read_only=True)
    yield connection
    connection.close()


@pytest.fixture
def planted_ids():
    if not PLANTED_PATH.exists():
        pytest.skip("planted_buyer_ids.json not found")
    with open(PLANTED_PATH) as f:
        return json.load(f)


def test_account_scores_have_valid_tiers(conn):
    rows = conn.sql("SELECT DISTINCT tier FROM main.account_scores").fetchall()
    tiers = {r[0] for r in rows}
    assert tiers.issubset({"hot", "warm", "watch", "cold"})


def test_timing_scores_between_0_and_100(conn):
    row = conn.sql("""
        SELECT MIN(timing_score), MAX(timing_score)
        FROM main.account_scores
    """).fetchall()[0]
    assert row[0] >= 0
    assert row[1] <= 100


def test_fit_scores_between_0_and_4(conn):
    row = conn.sql("""
        SELECT MIN(fit_score), MAX(fit_score)
        FROM main.account_scores
    """).fetchall()[0]
    assert row[0] >= 0
    assert row[1] <= 4


def test_planted_buyers_in_hot_tier(conn, planted_ids):
    placeholders = ",".join(f"'{pid}'" for pid in planted_ids)
    rows = conn.sql(f"""
        SELECT account_id, tier, timing_score
        FROM main.account_scores
        WHERE account_id IN ({placeholders})
        ORDER BY timing_score DESC
    """).fetchall()

    assert len(rows) == len(planted_ids)
    hot_count = sum(1 for r in rows if r[1] == "hot")
    assert hot_count >= len(planted_ids) * 0.8, (
        f"Expected >=80% of planted buyers in hot tier, got {hot_count}/{len(planted_ids)}"
    )


def test_alerts_within_attention_budget(conn):
    count = conn.sql("SELECT COUNT(*) FROM main.alerts").fetchall()[0][0]
    assert count <= 5, f"Expected <=5 alerts (attention budget), got {count}"


def test_all_alerts_have_explanations(conn):
    nulls = conn.sql("""
        SELECT COUNT(*) FROM main.alerts WHERE explanation IS NULL
    """).fetchall()[0][0]
    assert nulls == 0


def test_no_customers_in_scored_accounts(conn):
    count = conn.sql("""
        SELECT COUNT(*)
        FROM main.account_scores s
        JOIN bronze.accounts a ON s.account_id = a.account_id
        WHERE a.customer_status = 'customer'
    """).fetchall()[0][0]
    assert count == 0


def test_no_competitors_in_scored_accounts(conn):
    count = conn.sql("""
        SELECT COUNT(*)
        FROM main.account_scores s
        JOIN bronze.accounts a ON s.account_id = a.account_id
        WHERE list_contains(a.account_tags, 'competitor')
    """).fetchall()[0][0]
    assert count == 0
