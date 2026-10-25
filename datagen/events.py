import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from faker import Faker

from datagen.accounts import Account
from datagen.config import GenerationConfig
from datagen.people import Contact


@dataclass(frozen=True)
class Event:
    event_id: str
    event_type: str
    event_source: str
    contact_email: str | None
    email_domain: str
    ip_address: str | None
    event_properties: dict
    occurred_at: datetime
    ingested_at: datetime


def _random_timestamp(fake: Faker, start: datetime, end: datetime) -> datetime:
    delta = end - start
    random_seconds = fake.random_int(min=0, max=int(delta.total_seconds()))
    return start + timedelta(seconds=random_seconds)


def _generate_noise_events(
    accounts: list[Account],
    contacts: list[Contact],
    config: GenerationConfig,
    fake: Faker,
) -> list[Event]:
    events: list[Event] = []
    end_date = datetime.combine(config.score_date, datetime.min.time())
    start_date = end_date - timedelta(days=config.lookback_days)

    contacts_by_account: dict[str, list[Contact]] = {}
    for c in contacts:
        contacts_by_account.setdefault(c.account_id, []).append(c)

    noise_count = config.num_events - (config.num_planted_buyers * 80)

    for i in range(noise_count):
        account = fake.random_element(accounts)
        account_contacts = contacts_by_account.get(account.account_id, [])
        if not account_contacts:
            continue

        contact = fake.random_element(account_contacts)
        signal_type = fake.random_element(config.engagement_signals)
        source = config.source_for_signal[signal_type]
        occurred = _random_timestamp(fake, start_date, end_date)

        events.append(Event(
            event_id=str(uuid.uuid5(uuid.NAMESPACE_DNS, f"event-noise-{i}-{config.seed}")),
            event_type=signal_type,
            event_source=source,
            contact_email=contact.email,
            email_domain=account.domain,
            ip_address=fake.ipv4_private(),
            event_properties={"page_url": f"https://app.example.com/{signal_type}"},
            occurred_at=occurred,
            ingested_at=occurred + timedelta(minutes=fake.random_int(min=1, max=60)),
        ))

    return events


def _generate_planted_buyer_events(
    planted_accounts: list[Account],
    contacts: list[Contact],
    config: GenerationConfig,
    fake: Faker,
) -> list[Event]:
    events: list[Event] = []
    end_date = datetime.combine(config.score_date, datetime.min.time())

    contacts_by_account: dict[str, list[Contact]] = {}
    for c in contacts:
        contacts_by_account.setdefault(c.account_id, []).append(c)

    for account in planted_accounts:
        account_contacts = contacts_by_account.get(account.account_id, [])
        if len(account_contacts) < 3:
            continue

        active_people = account_contacts[:fake.random_int(min=3, max=min(5, len(account_contacts)))]
        recent_start = end_date - timedelta(days=fake.random_int(min=3, max=12))

        high_intent_signals = ["security_page", "pricing_page", "integration_docs", "product_trial"]
        trigger_signals = ["new_vp_hire", "funding_round"]

        for person in active_people:
            num_events = fake.random_int(min=8, max=20)
            for j in range(num_events):
                if j < 2:
                    signal_type = fake.random_element(high_intent_signals)
                elif j == 2:
                    signal_type = fake.random_element(trigger_signals)
                else:
                    signal_type = fake.random_element(
                        high_intent_signals + list(config.engagement_signals)
                    )

                source = config.source_for_signal[signal_type]
                occurred = _random_timestamp(fake, recent_start, end_date)

                events.append(Event(
                    event_id=str(uuid.uuid5(
                        uuid.NAMESPACE_DNS,
                        f"event-planted-{account.account_id}-{person.contact_id}-{j}-{config.seed}",
                    )),
                    event_type=signal_type,
                    event_source=source,
                    contact_email=person.email,
                    email_domain=account.domain,
                    ip_address=fake.ipv4_private(),
                    event_properties={
                        "page_url": f"https://app.example.com/{signal_type}",
                        "_planted": True,
                    },
                    occurred_at=occurred,
                    ingested_at=occurred + timedelta(minutes=fake.random_int(min=1, max=10)),
                ))

    return events


def generate_events(
    accounts: list[Account],
    contacts: list[Contact],
    config: GenerationConfig,
    fake: Faker,
    planted_account_ids: set[str],
) -> list[Event]:
    planted_accounts = [a for a in accounts if a.account_id in planted_account_ids]
    noise = _generate_noise_events(accounts, contacts, config, fake)
    planted = _generate_planted_buyer_events(planted_accounts, contacts, config, fake)
    return noise + planted
