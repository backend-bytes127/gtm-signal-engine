"""Dagster assets for the GTM Signal Engine pipeline."""
from dagster import asset, AssetExecutionContext, MaterializeResult, MetadataValue
from dagster_dbt import DbtCliResource, dbt_assets, DagsterDbtTranslator, DbtProject

from orchestration.constants import DBT_PROJECT_DIR, DBT_PROFILES_DIR

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
    """Run the datagen pipeline to populate bronze tables."""
    from datagen.__main__ import main as run_datagen

    context.log.info("Starting synthetic data generation...")
    run_datagen()
    context.log.info("Data generation complete.")

    import duckdb
    from orchestration.constants import DB_PATH

    conn = duckdb.connect(str(DB_PATH), read_only=True)
    account_count = conn.execute("SELECT COUNT(*) FROM bronze.accounts").fetchall()[0][0]
    contact_count = conn.execute("SELECT COUNT(*) FROM bronze.contacts").fetchall()[0][0]
    event_count = conn.execute("SELECT COUNT(*) FROM bronze.raw_events").fetchall()[0][0]
    conn.close()

    return MaterializeResult(
        metadata={
            "accounts": MetadataValue.int(account_count),
            "contacts": MetadataValue.int(contact_count),
            "events": MetadataValue.int(event_count),
        }
    )


@dbt_assets(
    manifest=dbt_project.manifest_path,
    dagster_dbt_translator=SignalEngineDbtTranslator(),
)
def dbt_signal_engine(context: AssetExecutionContext, dbt: DbtCliResource):
    """Run all dbt models: bronze staging → silver enrichment → gold scoring."""
    yield from dbt.cli(["build"], context=context).stream()
