with events as (
    select
        account_id,
        event_type,
        occurred_at
    from {{ ref('cleaned_events') }}
),

combos as (
    select * from {{ ref('combo_bonuses') }}
),

signal_a_events as (
    select
        e.account_id,
        c.combo_name,
        c.signal_a,
        c.signal_b,
        c.window_days,
        c.bonus_points,
        e.occurred_at as signal_a_at
    from events e
    inner join combos c on e.event_type = c.signal_a
),

matched as (
    select
        sa.account_id,
        sa.combo_name,
        sa.bonus_points,
        sa.signal_a,
        sa.signal_b,
        min(sa.signal_a_at) as first_signal_a,
        min(eb.occurred_at) as first_signal_b
    from signal_a_events sa
    inner join events eb
        on sa.account_id = eb.account_id
        and eb.event_type = sa.signal_b
        and eb.occurred_at >= sa.signal_a_at - interval '1 day' * sa.window_days
        and eb.occurred_at <= sa.signal_a_at + interval '1 day' * sa.window_days
    group by
        sa.account_id,
        sa.combo_name,
        sa.bonus_points,
        sa.signal_a,
        sa.signal_b
)

select
    account_id,
    combo_name,
    bonus_points,
    signal_a,
    signal_b,
    first_signal_a,
    first_signal_b
from matched
