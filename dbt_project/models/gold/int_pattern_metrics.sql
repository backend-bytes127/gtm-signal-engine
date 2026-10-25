with events as (
    select * from {{ ref('cleaned_events') }}
    where signal_category in ('trigger', 'engagement')
),

recent_events as (
    select *
    from events
    where occurred_at >= current_date - interval '14 days'
),

account_breadth as (
    select
        account_id,
        count(distinct contact_id) as distinct_people
    from recent_events
    group by account_id
),

account_channels as (
    select
        account_id,
        count(distinct event_source) as distinct_channels
    from recent_events
    group by account_id
),

last_7d as (
    select
        account_id,
        count(*) as events_7d
    from events
    where occurred_at >= current_date - interval '7 days'
    group by account_id
),

last_8w as (
    select
        account_id,
        count(*) * 1.0 / 8 as avg_events_per_week
    from events
    where occurred_at >= current_date - interval '56 days'
    group by account_id
),

spike as (
    select
        l7.account_id,
        l7.events_7d,
        coalesce(l8.avg_events_per_week, 1) as avg_weekly,
        l7.events_7d * 1.0 / greatest(coalesce(l8.avg_events_per_week, 1), 1) as activity_ratio
    from last_7d l7
    left join last_8w l8 on l7.account_id = l8.account_id
)

select
    coalesce(b.account_id, c.account_id, s.account_id) as account_id,
    coalesce(b.distinct_people, 0) as distinct_people,
    coalesce(c.distinct_channels, 0) as distinct_channels,
    coalesce(s.activity_ratio, 0) as activity_ratio,
    case
        when coalesce(b.distinct_people, 0) >= 3 then 1.6
        when coalesce(b.distinct_people, 0) = 2 then 1.3
        else 1.0
    end as breadth_multiplier,
    case
        when coalesce(c.distinct_channels, 0) >= 3 then 1.4
        when coalesce(c.distinct_channels, 0) >= 2 then 1.2
        else 1.0
    end as channel_mix_multiplier,
    case
        when coalesce(s.activity_ratio, 0) >= 8 then 1.8
        when coalesce(s.activity_ratio, 0) >= 4 then 1.5
        when coalesce(s.activity_ratio, 0) >= 2 then 1.2
        else 1.0
    end as spike_multiplier
from account_breadth b
full outer join account_channels c on b.account_id = c.account_id
full outer join spike s on coalesce(b.account_id, c.account_id) = s.account_id
