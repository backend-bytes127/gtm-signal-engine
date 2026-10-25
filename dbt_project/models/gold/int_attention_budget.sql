with unsuppressed as (
    select *
    from {{ ref('int_suppression') }}
    where not is_excluded
      and tier in ('hot', 'warm')
),

config as (
    select
        max(case when parameter = 'max_alerts_per_ae_per_day' then cast(value as int) end) as max_per_ae
    from {{ ref('suppression_config') }}
),

ranked as (
    select
        u.*,
        row_number() over (order by u.timing_score desc) as score_rank
    from unsuppressed u
)

select
    r.account_id,
    r.company_name,
    r.domain,
    r.tier,
    r.timing_score,
    r.fit_score,
    r.score_rank,
    case
        when r.score_rank <= c.max_per_ae then true
        else false
    end as within_budget
from ranked r
cross join config c
