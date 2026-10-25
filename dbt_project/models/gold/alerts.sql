with budgeted as (
    select * from {{ ref('int_attention_budget') }}
    where within_budget
),

explanations as (
    select
        account_id,
        explanation
    from {{ ref('score_explanations') }}
),

scores as (
    select
        account_id,
        base_score,
        breadth_multiplier,
        channel_mix_multiplier,
        spike_multiplier,
        combo_bonus,
        distinct_people,
        distinct_channels,
        activity_ratio,
        total_events,
        distinct_signal_types
    from {{ ref('account_scores') }}
)

select
    b.account_id,
    b.company_name,
    b.domain,
    b.tier,
    b.timing_score,
    b.fit_score,
    b.score_rank,
    s.base_score,
    s.breadth_multiplier,
    s.channel_mix_multiplier,
    s.spike_multiplier,
    s.combo_bonus,
    s.distinct_people,
    s.distinct_channels,
    s.activity_ratio,
    s.total_events,
    s.distinct_signal_types,
    e.explanation,
    current_timestamp as alerted_at
from budgeted b
left join explanations e on b.account_id = e.account_id
left join scores s on b.account_id = s.account_id
order by b.score_rank
