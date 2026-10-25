import uuid
from dataclasses import dataclass

from faker import Faker

from datagen.accounts import Account
from datagen.config import GenerationConfig


@dataclass(frozen=True)
class Contact:
    contact_id: str
    account_id: str
    email: str
    first_name: str
    last_name: str
    title: str
    seniority_level: str
    department: str
    contact_status: str


TITLES_BY_SENIORITY: dict[str, list[str]] = {
    "executive": [
        "VP Engineering", "VP Sales", "VP Product", "VP Security",
        "Head of Engineering", "Head of RevOps", "Head of IT",
        "CTO", "CISO", "CRO", "CPO",
    ],
    "manager": [
        "Engineering Manager", "Product Manager", "Security Manager",
        "IT Manager", "DevOps Lead", "Sales Manager",
        "Marketing Manager", "Platform Lead",
    ],
    "ic": [
        "Software Engineer", "DevOps Engineer", "Security Engineer",
        "Data Engineer", "Solutions Architect", "Sales Rep",
        "Marketing Specialist", "Product Analyst",
    ],
}


def generate_contacts(
    accounts: list[Account],
    config: GenerationConfig,
    fake: Faker,
) -> list[Contact]:
    contacts: list[Contact] = []

    for account in accounts:
        num_contacts = fake.random_int(
            min=config.contacts_per_account_range[0],
            max=config.contacts_per_account_range[1],
        )

        for j in range(num_contacts):
            seniority = fake.random_element(
                elements=("executive", "manager", "manager", "ic", "ic", "ic")
            )
            department = fake.random_element(config.departments)
            title = fake.random_element(TITLES_BY_SENIORITY[seniority])
            first = fake.first_name()
            last = fake.last_name()

            contact_status = "active"
            if fake.random_int(min=1, max=100) <= 3:
                contact_status = "dnc"
            elif fake.random_int(min=1, max=100) <= 2:
                contact_status = "bounced"

            contacts.append(Contact(
                contact_id=str(uuid.uuid5(
                    uuid.NAMESPACE_DNS,
                    f"contact-{account.account_id}-{j}-{config.seed}",
                )),
                account_id=account.account_id,
                email=f"{first.lower()}.{last.lower()}@{account.domain}",
                first_name=first,
                last_name=last,
                title=title,
                seniority_level=seniority,
                department=department,
                contact_status=contact_status,
            ))

    return contacts
