with base as (
    select * from {{ ref('int_base_scores') }}
),

fit as (
    select * from {{ ref('int_fit_scores') }}
),

patterns as (
    select * from {{ ref('int_pattern_metrics') }}
),

combos as (
    select
        account_id,
        sum(bonus_points) as combo_bonus
    from {{ ref('int_combo_matches') }}
    group by account_id
),

raw_scored as (
    select
        f.account_id,
        f.company_name,
        f.domain,
        f.industry,
        f.employee_count,
        f.region,
        f.fit_score,
        coalesce(b.base_score, 0) as base_score,
        coalesce(p.breadth_multiplier, 1.0) as breadth_multiplier,
        coalesce(p.channel_mix_multiplier, 1.0) as channel_mix_multiplier,
        coalesce(p.spike_multiplier, 1.0) as spike_multiplier,
        coalesce(c.combo_bonus, 0) as combo_bonus,
        coalesce(p.distinct_people, 0) as distinct_people,
        coalesce(p.distinct_channels, 0) as distinct_channels,
        coalesce(p.activity_ratio, 0) as activity_ratio,
        coalesce(b.total_events, 0) as total_events,
        coalesce(b.distinct_signal_types, 0) as distinct_signal_types,
        (
            coalesce(b.base_score, 0)
            * coalesce(p.breadth_multiplier, 1.0)
            * coalesce(p.channel_mix_multiplier, 1.0)
            * coalesce(p.spike_multiplier, 1.0)
        ) + coalesce(c.combo_bonus, 0) as raw_timing_score
    from fit f
    left join base b on f.account_id = b.account_id
    left join patterns p on f.account_id = p.account_id
    left join combos c on f.account_id = c.account_id
    where f.fit_score >= 2
),

scored as (
    select
        *,
        round(percent_rank() over (order by raw_timing_score) * 100, 1) as timing_score
    from raw_scored
)

select
    *,
    case
        when timing_score >= 70 then 'hot'
        when timing_score >= 40 then 'warm'
        when timing_score >= 20 then 'watch'
        else 'cold'
    end as tier,
    current_timestamp as scored_at
from scored
