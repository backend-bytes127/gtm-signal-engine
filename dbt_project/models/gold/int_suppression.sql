with scores as (
    select * from {{ ref('account_scores') }}
),

config as (
    select
        max(case when parameter = 'cooldown_days' then cast(value as int) end) as cooldown_days,
        max(case when parameter = 'cooldown_override_jump' then cast(value as double) end) as cooldown_override_jump
    from {{ ref('suppression_config') }}
),

exclusions as (
    select * from {{ ref('exclusion_rules') }}
),

accounts as (
    select * from {{ ref('stg_accounts') }}
),

excluded_accounts as (
    select distinct a.account_id
    from accounts a
    cross join exclusions e
    where
        (e.rule_name = 'open_deal' and a.deal_stage is not null)
        or (e.rule_name = 'existing_customer' and a.customer_status = 'customer')
        or (e.rule_name = 'competitor' and list_contains(a.account_tags, 'competitor'))
        or (e.rule_name = 'partner' and list_contains(a.account_tags, 'partner'))
),

suppressed as (
    select
        s.*,
        case
            when ea.account_id is not null then true
            else false
        end as is_excluded,
        'exclusion_rule' as suppression_reason
    from scores s
    left join excluded_accounts ea on s.account_id = ea.account_id
)

select
    account_id,
    company_name,
    domain,
    tier,
    timing_score,
    fit_score,
    is_excluded,
    case when is_excluded then suppression_reason else null end as suppression_reason
from suppressed
