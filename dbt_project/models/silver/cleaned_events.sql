with events as (
    select * from {{ ref('stg_raw_events') }}
),

contacts as (
    select * from {{ ref('stg_contacts') }}
),

accounts as (
    select * from {{ ref('stg_accounts') }}
),

taxonomy as (
    select * from {{ ref('signal_taxonomy') }}
),

event_with_contact as (
    select
        e.event_id,
        e.event_type,
        e.event_source,
        e.contact_email,
        e.email_domain,
        e.occurred_at,
        c.contact_id,
        c.account_id
    from events e
    left join contacts c on e.contact_email = c.email
),

event_with_account as (
    select
        ewc.*,
        coalesce(ewc.account_id, a.account_id) as resolved_account_id
    from event_with_contact ewc
    left join accounts a on ewc.email_domain = a.domain
    where coalesce(ewc.account_id, a.account_id) is not null
),

with_taxonomy as (
    select
        ewa.event_id,
        ewa.event_type,
        t.signal_category,
        ewa.event_source,
        ewa.contact_id,
        ewa.resolved_account_id as account_id,
        t.base_weight,
        t.half_life_days,
        ewa.occurred_at
    from event_with_account ewa
    inner join taxonomy t on ewa.event_type = t.signal_type
),

exclude_noise as (
    select
        wt.*
    from with_taxonomy wt
    inner join accounts a on wt.account_id = a.account_id
    where a.customer_status != 'customer'
      and not list_contains(a.account_tags, 'competitor')
      and not list_contains(a.account_tags, 'partner')
)

select * from exclude_noise
