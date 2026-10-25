"""Tests for synthetic data generation."""
from faker import Faker

from datagen.accounts import generate_accounts
from datagen.config import GenerationConfig
from datagen.events import generate_events
from datagen.people import generate_contacts


def _make_config() -> GenerationConfig:
    return GenerationConfig(num_accounts=20, num_events=200, num_planted_buyers=3, seed=42)


def test_generates_correct_number_of_accounts():
    config = _make_config()
    fake = Faker()
    Faker.seed(config.seed)
    accounts = generate_accounts(config, fake)
    assert len(accounts) == config.num_accounts


def test_accounts_have_required_fields():
    config = _make_config()
    fake = Faker()
    Faker.seed(config.seed)
    accounts = generate_accounts(config, fake)
    for a in accounts:
        assert a.account_id
        assert a.company_name
        assert a.domain
        assert a.customer_status in ("prospect", "customer")


def test_account_tags_are_correct():
    config = _make_config()
    fake = Faker()
    Faker.seed(config.seed)
    accounts = generate_accounts(config, fake)
    competitors = [a for a in accounts if "competitor" in (a.account_tags or [])]
    partners = [a for a in accounts if "partner" in (a.account_tags or [])]
    assert len(competitors) > 0
    assert len(partners) > 0


def test_contacts_generated_for_each_account():
    config = _make_config()
    fake = Faker()
    Faker.seed(config.seed)
    accounts = generate_accounts(config, fake)
    contacts = generate_contacts(accounts, config, fake)
    assert len(contacts) > len(accounts)

    account_ids_with_contacts = {c.account_id for c in contacts}
    for a in accounts:
        assert a.account_id in account_ids_with_contacts


def test_contacts_have_valid_seniority():
    config = _make_config()
    fake = Faker()
    Faker.seed(config.seed)
    accounts = generate_accounts(config, fake)
    contacts = generate_contacts(accounts, config, fake)
    valid_seniority = {"executive", "manager", "ic"}
    for c in contacts:
        assert c.seniority_level in valid_seniority


def test_events_include_planted_buyer_events():
    config = GenerationConfig(num_accounts=100, num_events=2000, num_planted_buyers=3, seed=42)
    fake = Faker()
    Faker.seed(config.seed)
    accounts = generate_accounts(config, fake)
    contacts = generate_contacts(accounts, config, fake)

    good_prospects = [
        a for a in accounts
        if a.customer_status == "prospect"
        and not a.account_tags
        and a.deal_stage is None
        and a.industry in config.target_industries
        and config.target_employee_range[0] <= a.employee_count <= config.target_employee_range[1]
    ]
    planted_ids = {a.account_id for a in good_prospects[:config.num_planted_buyers]}

    events = generate_events(accounts, contacts, config, fake, planted_ids)
    planted_events = [e for e in events if e.event_properties.get("_planted")]
    assert len(planted_events) > 0


def test_event_types_are_valid():
    config = _make_config()
    fake = Faker()
    Faker.seed(config.seed)
    accounts = generate_accounts(config, fake)
    contacts = generate_contacts(accounts, config, fake)
    events = generate_events(accounts, contacts, config, fake, set())

    valid_types = set(config.engagement_signals + config.trigger_signals + config.fit_signals)
    for e in events:
        assert e.event_type in valid_types
