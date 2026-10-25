import uuid
from dataclasses import dataclass

from faker import Faker

from datagen.config import GenerationConfig


@dataclass(frozen=True)
class Account:
    account_id: str
    company_name: str
    domain: str
    industry: str
    employee_count: int
    region: str
    tech_stack: list[str]
    customer_status: str
    account_tags: list[str]
    deal_stage: str | None
    assigned_ae_id: str


def generate_accounts(config: GenerationConfig, fake: Faker) -> list[Account]:
    accounts: list[Account] = []
    ae_ids = [f"ae_{i}" for i in range(1, 11)]

    for i in range(config.num_accounts):
        industry = fake.random_element(
            config.target_industries + ("Retail", "Education", "Manufacturing", "Media", "Logistics")
        )
        region = fake.random_element(
            config.target_regions + ("LATAM", "MEA", "EU-East")
        )
        employee_count = fake.random_int(min=10, max=50000)

        tech_stack = list(fake.random_elements(
            config.tech_stack_options,
            length=fake.random_int(min=1, max=6),
            unique=True,
        ))

        tags: list[str] = []
        customer_status = "prospect"
        deal_stage: str | None = None

        if i < 5:
            tags = ["competitor"]
            domain = config.competitor_domains[i % len(config.competitor_domains)]
        elif i < 8:
            tags = ["partner"]
            domain = config.partner_domains[i % len(config.partner_domains)]
        elif i < 15:
            customer_status = "customer"
            domain = fake.domain_name()
        elif i < 25:
            deal_stage = fake.random_element(["discovery", "evaluation", "negotiation"])
            domain = fake.domain_name()
        else:
            domain = fake.domain_name()

        accounts.append(Account(
            account_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"account-{i}-{config.seed}")),
            company_name=fake.company(),
            domain=domain,
            industry=industry,
            employee_count=employee_count,
            region=region,
            tech_stack=tech_stack,
            customer_status=customer_status,
            account_tags=tags,
            deal_stage=deal_stage,
            assigned_ae_id=fake.random_element(ae_ids),
        ))

    return accounts
