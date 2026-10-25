"""Shared constants for Dagster orchestration."""
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
DBT_PROJECT_DIR = PROJECT_ROOT / "dbt_project"
DBT_PROFILES_DIR = DBT_PROJECT_DIR
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "signal_engine.duckdb"
