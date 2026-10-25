"""Dagster schedules for the GTM Signal Engine."""
from dagster import ScheduleDefinition, define_asset_job

scoring_pipeline_job = define_asset_job(
    name="daily_scoring_pipeline",
    description="Full pipeline: generate data → seed → score → alert.",
    selection="*",
)

daily_scoring_schedule = ScheduleDefinition(
    job=scoring_pipeline_job,
    cron_schedule="0 6 * * *",
    description="Run scoring pipeline daily at 6:00 AM UTC.",
)
