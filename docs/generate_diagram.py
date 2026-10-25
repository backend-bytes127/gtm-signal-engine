"""Generate enterprise architecture diagram using the diagrams library."""
from pathlib import Path

from diagrams import Cluster, Diagram, Edge
from diagrams.custom import Custom
from diagrams.onprem.analytics import Dbt
from diagrams.onprem.database import PostgreSQL
from diagrams.onprem.workflow import Airflow
from diagrams.programming.language import Python
from diagrams.saas.chat import Slack
from diagrams.generic.storage import Storage

DOCS_DIR = Path(__file__).parent


with Diagram(
    "GTM Signal Engine",
    filename=str(DOCS_DIR / "pipeline_architecture"),
    show=False,
    direction="LR",
    graph_attr={
        "fontsize": "28",
        "bgcolor": "white",
        "pad": "0.8",
        "nodesep": "0.8",
        "ranksep": "1.2",
    },
):
    with Cluster("Signal Sources"):
        website = Storage("Website\nTracking")
        crm = Storage("CRM\nEvents")
        email = Storage("Email\nEngagement")
        ads = Storage("Ad\nPlatforms")
        enrichment = Storage("Enrichment\nProviders")
        triggers = Storage("Trigger\nEvents")

    with Cluster("Orchestration"):
        dagster = Airflow("Dagster\n(Daily 6AM UTC)")

    with Cluster("Data Generation"):
        faker = Python("Faker\nSynthetic Data")

    with Cluster("DuckDB — Medallion Architecture"):
        with Cluster("Bronze (Raw)"):
            raw_accounts = PostgreSQL("accounts")
            raw_contacts = PostgreSQL("contacts")
            raw_events = PostgreSQL("raw_events")

        with Cluster("Silver (Enriched)"):
            cleaned = Dbt("cleaned_events\n(joined + taxonomy)")

        with Cluster("Gold (Scored)"):
            base = Dbt("base_scores\n(time-decayed)")
            fit = Dbt("fit_scores\n(ICP 0-4)")
            patterns = Dbt("pattern_metrics\n(breadth × channel × spike)")
            combos = Dbt("combo_matches\n(signal pairs)")
            scores = Dbt("account_scores\n(final percentile)")

        with Cluster("Activation"):
            suppression = Dbt("suppression\n+ exclusions")
            budget = Dbt("attention_budget\n(5/AE/day cap)")
            alerts = Dbt("alerts\n+ explanations")

    with Cluster("Delivery (M3)"):
        hubspot = Storage("HubSpot\nCRM Push")
        slack = Slack("Slack\nDigest")

    with Cluster("Feedback (M4)"):
        feedback = Storage("Rep Feedback\n(accept/dismiss)")

    # Source → Bronze
    sources = [website, crm, email, ads, enrichment, triggers]
    for s in sources:
        s >> Edge(style="dashed", color="gray") >> raw_events

    # Dagster orchestrates
    dagster >> Edge(color="darkblue", style="bold") >> faker
    faker >> Edge(color="darkblue") >> raw_accounts
    faker >> Edge(color="darkblue") >> raw_contacts
    faker >> Edge(color="darkblue") >> raw_events

    dagster >> Edge(color="darkblue", style="bold") >> cleaned

    # Bronze → Silver
    raw_events >> Edge(color="orange") >> cleaned
    raw_contacts >> Edge(color="orange") >> cleaned
    raw_accounts >> Edge(color="orange") >> cleaned

    # Silver → Gold
    cleaned >> Edge(color="green") >> base
    cleaned >> Edge(color="green") >> patterns
    cleaned >> Edge(color="green") >> combos

    base >> Edge(color="green") >> scores
    fit >> Edge(color="green") >> scores
    patterns >> Edge(color="green") >> scores
    combos >> Edge(color="green") >> scores

    # Gold → Activation
    scores >> Edge(color="red") >> suppression
    suppression >> Edge(color="red") >> budget
    budget >> Edge(color="red") >> alerts

    # Activation → Delivery
    alerts >> Edge(color="purple", style="bold") >> hubspot
    alerts >> Edge(color="purple", style="bold") >> slack

    # Feedback loop
    hubspot >> Edge(color="gray", style="dashed") >> feedback
    feedback >> Edge(color="gray", style="dashed", label="tune weights") >> base
