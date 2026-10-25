"""Dagster Definitions — single entry point for the signal engine."""
from dagster import Definitions
from dagster_dbt import DbtCliResource

from orchestration.assets import synthetic_data, dbt_signal_engine, deliver_alerts
from orchestration.constants import DBT_PROJECT_DIR, DBT_PROFILES_DIR
from orchestration.schedules import daily_scoring_schedule

defs = Definitions(
    assets=[synthetic_data, dbt_signal_engine, deliver_alerts],
    schedules=[daily_scoring_schedule],
    resources={
        "dbt": DbtCliResource(
            project_dir=DBT_PROJECT_DIR,
            profiles_dir=DBT_PROFILES_DIR,
        ),
    },
)
