with accounts as (
    select * from {{ ref('stg_accounts') }}
),

fit_scoring as (
    select
        account_id,
        company_name,
        domain,
        industry,
        employee_count,
        region,
        tech_stack,
        case when industry in ('Software', 'Financial Services', 'Healthcare Tech', 'Cybersecurity', 'Cloud Infrastructure')
             then 1 else 0 end as industry_match,
        case when employee_count between 50 and 5000
             then 1 else 0 end as size_match,
        case when region in ('US-West', 'US-East', 'US-Central', 'EU-West', 'APAC')
             then 1 else 0 end as region_match,
        case when list_has_any(tech_stack, ['Salesforce', 'HubSpot', 'Snowflake', 'Segment', 'Slack'])
             then 1 else 0 end as tech_match
    from accounts
    where customer_status = 'prospect'
      and not list_contains(account_tags, 'competitor')
      and not list_contains(account_tags, 'partner')
)

select
    account_id,
    company_name,
    domain,
    industry,
    employee_count,
    region,
    (industry_match + size_match + region_match + tech_match) as fit_score,
    industry_match,
    size_match,
    region_match,
    tech_match
from fit_scoring
