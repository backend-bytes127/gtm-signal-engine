with scores as (
    select * from {{ ref('account_scores') }}
),

combos as (
    select
        account_id,
        list(combo_name order by bonus_points desc) as combo_names
    from {{ ref('int_combo_matches') }}
    group by account_id
),

explanations as (
    select
        s.account_id,
        s.company_name,
        s.tier,
        s.timing_score,
        s.fit_score,
        concat(
            s.company_name,
            ' scored ', round(s.timing_score, 1), ' (', s.tier, ')',
            ' with fit ', s.fit_score, '/4.',
            case when s.distinct_people >= 3
                then concat(' ', s.distinct_people, ' people engaged (breadth ×', s.breadth_multiplier, ').')
                when s.distinct_people = 2
                then concat(' ', s.distinct_people, ' people engaged (breadth ×', s.breadth_multiplier, ').')
                else ''
            end,
            case when s.distinct_channels >= 2
                then concat(' ', s.distinct_channels, ' channels active (mix ×', s.channel_mix_multiplier, ').')
                else ''
            end,
            case when s.activity_ratio >= 2
                then concat(' Activity spike ', round(s.activity_ratio, 1), '× vs avg (×', s.spike_multiplier, ').')
                else ''
            end,
            case when s.combo_bonus > 0
                then concat(' Combos: +', s.combo_bonus, ' pts.')
                else ''
            end
        ) as explanation
    from scores s
    left join combos c on s.account_id = c.account_id
)

select * from explanations
