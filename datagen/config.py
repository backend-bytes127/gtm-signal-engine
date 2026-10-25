from dataclasses import dataclass, field
from datetime import date


@dataclass(frozen=True)
class GenerationConfig:
    num_accounts: int = 500
    contacts_per_account_range: tuple[int, int] = (3, 15)
    num_events: int = 100_000
    num_planted_buyers: int = 10
    score_date: date = field(default_factory=date.today)
    lookback_days: int = 90
    db_path: str = "data/signal_engine.duckdb"
    seed: int = 42

    target_industries: tuple[str, ...] = (
        "Software", "Financial Services", "Healthcare Tech",
        "Cybersecurity", "Cloud Infrastructure",
    )
    target_regions: tuple[str, ...] = (
        "US-West", "US-East", "US-Central", "EU-West", "APAC",
    )
    target_employee_range: tuple[int, int] = (50, 5000)

    seniority_levels: tuple[str, ...] = ("executive", "manager", "ic")
    departments: tuple[str, ...] = (
        "Engineering", "Product", "Security", "IT", "Sales",
        "Marketing", "Operations", "Finance",
    )

    event_sources: tuple[str, ...] = (
        "website", "product", "ads", "email", "enrichment", "third_party",
    )

    engagement_signals: tuple[str, ...] = (
        "security_page", "pricing_page", "integration_docs",
        "product_trial", "docs_page", "demo_request",
        "case_study", "ad_click", "email_click", "blog_visit",
    )
    trigger_signals: tuple[str, ...] = (
        "new_vp_hire", "funding_round", "relevant_job_posts", "tool_change",
    )
    fit_signals: tuple[str, ...] = (
        "company_size", "target_industry", "target_region", "tech_stack_match",
    )

    source_for_signal: dict[str, str] = field(default_factory=lambda: {
        "security_page": "website",
        "pricing_page": "website",
        "integration_docs": "website",
        "docs_page": "website",
        "case_study": "website",
        "blog_visit": "website",
        "product_trial": "product",
        "demo_request": "website",
        "ad_click": "ads",
        "email_click": "email",
        "new_vp_hire": "enrichment",
        "funding_round": "enrichment",
        "relevant_job_posts": "enrichment",
        "tool_change": "third_party",
        "company_size": "enrichment",
        "target_industry": "enrichment",
        "target_region": "enrichment",
        "tech_stack_match": "third_party",
    })

    competitor_domains: tuple[str, ...] = (
        "competitor-a.com", "competitor-b.com", "rival-inc.com",
    )
    internal_domains: tuple[str, ...] = (
        "ourcompany.com", "ourcompany.io",
    )
    partner_domains: tuple[str, ...] = (
        "partner-co.com", "integration-partner.com",
    )

    tech_stack_options: tuple[str, ...] = (
        "Salesforce", "HubSpot", "Outreach", "Gong", "ZoomInfo",
        "6sense", "Snowflake", "Databricks", "dbt", "Segment",
        "Marketo", "Pardot", "Drift", "Intercom", "Slack",
    )
    compatible_tools: tuple[str, ...] = (
        "Salesforce", "HubSpot", "Snowflake", "Segment", "Slack",
    )
    competitor_tools: tuple[str, ...] = (
        "6sense", "Marketo",
    )
