"""Generate synthetic data and load into DuckDB."""
import json
import os
from datetime import datetime
from pathlib import Path

import duckdb
from faker import Faker

from datagen.accounts import generate_accounts
from datagen.config import GenerationConfig
from datagen.events import generate_events
from datagen.people import generate_contacts


def setup_database(db_path: str) -> duckdb.DuckDBPyConnection:
    Path(db_path).parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(db_path)

    conn.execute("CREATE SCHEMA IF NOT EXISTS bronze")
    conn.execute("CREATE SCHEMA IF NOT EXISTS silver")
    conn.execute("CREATE SCHEMA IF NOT EXISTS gold")
    conn.execute("CREATE SCHEMA IF NOT EXISTS seeds")

    conn.execute("DROP TABLE IF EXISTS bronze.accounts")
    conn.execute("""
        CREATE TABLE bronze.accounts (
            account_id VARCHAR PRIMARY KEY,
            company_name VARCHAR NOT NULL,
            domain VARCHAR NOT NULL,
            industry VARCHAR,
            employee_count INTEGER,
            region VARCHAR,
            tech_stack VARCHAR[],
            customer_status VARCHAR NOT NULL,
            account_tags VARCHAR[],
            deal_stage VARCHAR,
            assigned_ae_id VARCHAR,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("DROP TABLE IF EXISTS bronze.contacts")
    conn.execute("""
        CREATE TABLE bronze.contacts (
            contact_id VARCHAR PRIMARY KEY,
            account_id VARCHAR NOT NULL,
            email VARCHAR NOT NULL,
            first_name VARCHAR,
            last_name VARCHAR,
            title VARCHAR,
            seniority_level VARCHAR,
            department VARCHAR,
            contact_status VARCHAR NOT NULL,
            created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.execute("DROP TABLE IF EXISTS bronze.raw_events")
    conn.execute("""
        CREATE TABLE bronze.raw_events (
            event_id VARCHAR PRIMARY KEY,
            event_type VARCHAR NOT NULL,
            event_source VARCHAR NOT NULL,
            contact_email VARCHAR,
            email_domain VARCHAR,
            ip_address VARCHAR,
            event_properties JSON,
            occurred_at TIMESTAMP NOT NULL,
            ingested_at TIMESTAMP NOT NULL
        )
    """)

    return conn


def load_accounts(conn: duckdb.DuckDBPyConnection, accounts: list) -> None:
    rows = [
        (
            a.account_id, a.company_name, a.domain, a.industry,
            a.employee_count, a.region, a.tech_stack, a.customer_status,
            a.account_tags, a.deal_stage, a.assigned_ae_id, datetime.now(),
        )
        for a in accounts
    ]
    conn.executemany(
        """INSERT INTO bronze.accounts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def load_contacts(conn: duckdb.DuckDBPyConnection, contacts: list) -> None:
    rows = [
        (
            c.contact_id, c.account_id, c.email, c.first_name,
            c.last_name, c.title, c.seniority_level, c.department,
            c.contact_status, datetime.now(),
        )
        for c in contacts
    ]
    conn.executemany(
        """INSERT INTO bronze.contacts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def load_events(conn: duckdb.DuckDBPyConnection, events: list) -> None:
    rows = [
        (
            e.event_id, e.event_type, e.event_source, e.contact_email,
            e.email_domain, e.ip_address, json.dumps(e.event_properties),
            e.occurred_at, e.ingested_at,
        )
        for e in events
    ]
    conn.executemany(
        """INSERT INTO bronze.raw_events VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        rows,
    )


def main() -> None:
    config = GenerationConfig()
    fake = Faker()
    Faker.seed(config.seed)

    print(f"Generating {config.num_accounts} accounts...")
    accounts = generate_accounts(config, fake)

    good_prospect_accounts = [
        a for a in accounts
        if a.customer_status == "prospect"
        and not a.account_tags
        and a.deal_stage is None
        and a.industry in config.target_industries
        and config.target_employee_range[0] <= a.employee_count <= config.target_employee_range[1]
    ]

    planted_accounts = good_prospect_accounts[:config.num_planted_buyers]
    planted_ids = {a.account_id for a in planted_accounts}

    print(f"Selected {len(planted_ids)} planted buyer accounts:")
    for a in planted_accounts:
        print(f"  - {a.company_name} ({a.domain}) [{a.industry}, {a.employee_count} emp]")

    print(f"\nGenerating contacts...")
    contacts = generate_contacts(accounts, config, fake)
    print(f"  {len(contacts)} contacts generated")

    print(f"\nGenerating ~{config.num_events} events ({config.num_planted_buyers} planted buyers)...")
    events = generate_events(accounts, contacts, config, fake, planted_ids)
    print(f"  {len(events)} events generated")

    print(f"\nLoading into DuckDB at {config.db_path}...")
    conn = setup_database(config.db_path)
    load_accounts(conn, accounts)
    load_contacts(conn, contacts)
    load_events(conn, events)

    print("\nVerification:")
    result = conn.execute("SELECT COUNT(*) FROM bronze.accounts").fetchone()
    print(f"  Accounts: {result[0]}")
    result = conn.execute("SELECT COUNT(*) FROM bronze.contacts").fetchone()
    print(f"  Contacts: {result[0]}")
    result = conn.execute("SELECT COUNT(*) FROM bronze.raw_events").fetchone()
    print(f"  Events:   {result[0]}")

    planted_event_count = conn.execute("""
        SELECT COUNT(*)
        FROM bronze.raw_events
        WHERE json_extract_string(event_properties, '$._planted') = 'true'
    """).fetchone()
    print(f"  Planted buyer events: {planted_event_count[0]}")

    planted_ids_path = Path(config.db_path).parent / "planted_buyer_ids.json"
    with open(planted_ids_path, "w") as f:
        json.dump(list(planted_ids), f, indent=2)
    print(f"\nPlanted buyer IDs saved to {planted_ids_path}")

    conn.close()
    print("\nData generation complete!")


if __name__ == "__main__":
    main()
