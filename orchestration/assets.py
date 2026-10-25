"""Dagster assets for the GTM Signal Engine pipeline."""
import subprocess
import sys

from dagster import asset, AssetExecutionContext, MaterializeResult, MetadataValue
from dagster_dbt import DbtCliResource, dbt_assets, DagsterDbtTranslator, DbtProject

from orchestration.constants import DBT_PROJECT_DIR, DBT_PROFILES_DIR, PROJECT_ROOT

dbt_project = DbtProject(
    project_dir=DBT_PROJECT_DIR,
    profiles_dir=DBT_PROFILES_DIR,
)
dbt_project.prepare_if_dev()


class SignalEngineDbtTranslator(DagsterDbtTranslator):
    """Maps dbt models to Dagster asset keys with group tagging."""

    def get_group_name(self, dbt_resource_props: dict) -> str | None:
        fqn = dbt_resource_props.get("fqn", [])
        if len(fqn) >= 2:
            folder = fqn[1]
            if folder in ("bronze", "silver", "gold"):
                return folder
            if folder == "seeds":
                return "seeds"
        return "default"


@asset(
    group_name="bronze",
    description="Generate synthetic accounts, contacts, and events into DuckDB.",
)
def synthetic_data(context: AssetExecutionContext) -> MaterializeResult:
    """Run the datagen pipeline as a subprocess to avoid DuckDB lock conflicts."""
    context.log.info("Starting synthetic data generation (subprocess)...")
    result = subprocess.run(
        [sys.executable, "-m", "datagen"],
        cwd=str(PROJECT_ROOT),
        env={**__import__("os").environ, "PYTHONPATH": str(PROJECT_ROOT)},
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        context.log.error("datagen stderr: %s", result.stderr)
        raise RuntimeError(f"datagen failed:\n{result.stderr}")
    context.log.info(result.stdout)

    counts = subprocess.run(
        [
            sys.executable, "-c",
            "import duckdb, json; "
            f"c = duckdb.connect('{PROJECT_ROOT / 'data' / 'signal_engine.duckdb'}', read_only=True); "
            "r = {t: c.execute(f'SELECT COUNT(*) FROM bronze.{t}').fetchone()[0] "
            "for t in ['accounts','contacts','raw_events']}; "
            "c.close(); print(json.dumps(r))",
        ],
        capture_output=True,
        text=True,
    )
    meta = __import__("json").loads(counts.stdout) if counts.returncode == 0 else {}

    return MaterializeResult(
        metadata={
            "accounts": MetadataValue.int(meta.get("accounts", 0)),
            "contacts": MetadataValue.int(meta.get("contacts", 0)),
            "events": MetadataValue.int(meta.get("raw_events", 0)),
        }
    )


@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=SignalEngineDbtTranslator(),
)
def dbt_signal_engine(context: AssetExecutionContext, dbt: DbtCliResource):
    """Run all dbt models: bronze staging → silver enrichment → gold scoring."""
    yield from dbt.cli(["build"], context=context).stream()


@asset(
    group_name="activation",
    deps=["alerts"],
    description="Push scored alerts to HubSpot and Slack.",
)
def deliver_alerts(context: AssetExecutionContext) -> MaterializeResult:
    """Load alerts from DuckDB and push to HubSpot + Slack."""
    from activation.runner import load_alerts
    from activation.hubspot import push_alerts
    from activation.slack import send_daily_digest, send_hot_alerts

    alerts = load_alerts()
    context.log.info("Loaded %d alerts", len(alerts))

    hubspot_results = push_alerts(alerts)
    pushed = sum(1 for r in hubspot_results if r["status"] in ("pushed", "dry_run"))

    digest_result = send_daily_digest(alerts)
    hot = [a for a in alerts if a.tier == "hot"]
    hot_results = send_hot_alerts(alerts) if hot else []

    return MaterializeResult(
        metadata={
            "total_alerts": MetadataValue.int(len(alerts)),
            "hubspot_pushed": MetadataValue.int(pushed),
            "slack_digest": MetadataValue.text(digest_result["status"]),
            "hot_alerts_sent": MetadataValue.int(len(hot_results)),
        }
    )
