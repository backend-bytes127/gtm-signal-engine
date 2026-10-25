with events as (
    select * from {{ ref('cleaned_events') }}
    where signal_category in ('trigger', 'engagement')
),

decayed as (
    select
        account_id,
        event_id,
        event_type,
        base_weight,
        half_life_days,
        occurred_at,
        current_date - cast(occurred_at as date) as age_days,
        base_weight * power(2.0, -1.0 * (current_date - cast(occurred_at as date)) / nullif(half_life_days, 0))
            as decayed_weight
    from events
    where half_life_days > 0
)

select
    account_id,
    sum(decayed_weight) as base_score,
    count(*) as total_events,
    count(distinct event_type) as distinct_signal_types
from decayed
group by account_id
