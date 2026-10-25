"""Signal effectiveness analysis and weight tuning recommendations."""
from __future__ import annotations

import csv
import logging
from dataclasses import dataclass
from pathlib import Path

import duckdb

logger = logging.getLogger(__name__)

DB_PATH = Path(__file__).parent.parent / "data" / "signal_engine.duckdb"
SEEDS_DIR = Path(__file__).parent.parent / "dbt_project" / "seeds"


@dataclass(frozen=True)
class SignalEffectiveness:
    signal_type: str
    total_alerts: int
    accepted: int
    dismissed: int
    converted: int
    stale: int
    effectiveness_pct: float
    current_weight: float
    recommended_weight: float


def analyze_effectiveness(db_path: str | Path = DB_PATH) -> list[SignalEffectiveness]:
    conn = duckdb.connect(str(db_path), read_only=True)

    taxonomy = {}
    try:
        for row in conn.sql("SELECT signal_type, base_weight FROM main_seeds.signal_taxonomy").fetchall():
            taxonomy[row[0]] = row[1]
    except duckdb.CatalogException:
        pass

    try:
        rows = conn.sql("""
            WITH recent_alerts AS (
                SELECT
                    a.account_id,
                    a.tier
                FROM main.account_scores a
            ),
            feedback_signals AS (
                SELECT
                    ce.event_type,
                    f.outcome,
                    COUNT(*) as cnt
                FROM gold.alert_feedback f
                INNER JOIN main.cleaned_events ce
                    ON f.account_id = ce.account_id
                    AND ce.occurred_at >= f.alert_date - INTERVAL '14 days'
                    AND ce.occurred_at <= f.alert_date
                GROUP BY ce.event_type, f.outcome
            ),
            pivoted AS (
                SELECT
                    event_type,
                    SUM(cnt) as total,
                    COALESCE(SUM(cnt) FILTER (WHERE outcome = 'accepted'), 0) as accepted,
                    COALESCE(SUM(cnt) FILTER (WHERE outcome = 'dismissed'), 0) as dismissed,
                    COALESCE(SUM(cnt) FILTER (WHERE outcome = 'converted'), 0) as converted,
                    COALESCE(SUM(cnt) FILTER (WHERE outcome = 'stale'), 0) as stale
                FROM feedback_signals
                GROUP BY event_type
            )
            SELECT
                event_type, total, accepted, dismissed, converted, stale,
                ROUND((accepted + converted) * 100.0 / NULLIF(total, 0), 1) as eff_pct
            FROM pivoted
            ORDER BY eff_pct DESC
        """).fetchall()
    except duckdb.CatalogException:
        logger.warning("No feedback data found — cannot analyze effectiveness")
        conn.close()
        return []

    conn.close()

    results = []
    for row in rows:
        signal_type = row[0]
        current_weight = taxonomy.get(signal_type, 5.0)
        eff_pct = row[6] or 0.0

        if eff_pct >= 80:
            recommended = min(current_weight * 1.3, 20.0)
        elif eff_pct >= 50:
            recommended = current_weight
        elif eff_pct >= 30:
            recommended = max(current_weight * 0.8, 1.0)
        else:
            recommended = max(current_weight * 0.5, 1.0)

        results.append(SignalEffectiveness(
            signal_type=signal_type,
            total_alerts=row[1],
            accepted=row[2],
            dismissed=row[3],
            converted=row[4],
            stale=row[5],
            effectiveness_pct=eff_pct,
            current_weight=current_weight,
            recommended_weight=round(recommended, 1),
        ))

    return results


def print_effectiveness_report(results: list[SignalEffectiveness]) -> None:
    if not results:
        print("No feedback data available for effectiveness analysis.")
        return

    print("\n" + "=" * 90)
    print("SIGNAL EFFECTIVENESS REPORT")
    print("=" * 90)
    print(f"{'Signal Type':<25} {'Total':>6} {'Accept':>7} {'Dismiss':>8} {'Convert':>8} {'Eff%':>6} {'Curr Wt':>8} {'Rec Wt':>7}")
    print("-" * 90)

    for r in results:
        change = ""
        if r.recommended_weight > r.current_weight:
            change = " ↑"
        elif r.recommended_weight < r.current_weight:
            change = " ↓"

        print(
            f"{r.signal_type:<25} {r.total_alerts:>6} {r.accepted:>7} "
            f"{r.dismissed:>8} {r.converted:>8} {r.effectiveness_pct:>5.1f}% "
            f"{r.current_weight:>7.1f} {r.recommended_weight:>6.1f}{change}"
        )

    print("=" * 90)

    adjustments = [r for r in results if r.recommended_weight != r.current_weight]
    if adjustments:
        print(f"\n{len(adjustments)} weight adjustments recommended.")
        print("Run `python -m activation.effectiveness --apply` to update seed files.")
    else:
        print("\nAll weights look well-calibrated. No changes needed.")


def apply_weight_updates(results: list[SignalEffectiveness], seeds_dir: Path = SEEDS_DIR) -> Path:
    taxonomy_path = seeds_dir / "signal_taxonomy.csv"

    with open(taxonomy_path) as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames or []

    weight_map = {r.signal_type: r.recommended_weight for r in results}

    updated_rows = []
    changes = 0
    for row in rows:
        new_row = dict(row)
        if row["signal_type"] in weight_map:
            old_weight = float(row["base_weight"])
            new_weight = weight_map[row["signal_type"]]
            if old_weight != new_weight:
                new_row["base_weight"] = str(new_weight)
                changes += 1
                logger.info(
                    "Updated %s weight: %.1f → %.1f",
                    row["signal_type"], old_weight, new_weight,
                )
        updated_rows.append(new_row)

    output_path = seeds_dir / "signal_taxonomy.csv"
    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(updated_rows)

    logger.info("Updated %d weights in %s", changes, output_path)
    return output_path


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)
    results = analyze_effectiveness()
    print_effectiveness_report(results)

    if "--apply" in sys.argv and results:
        apply_weight_updates(results)
        print("\nWeights updated in dbt seed file. Run `dbt seed && dbt run` to apply.")
