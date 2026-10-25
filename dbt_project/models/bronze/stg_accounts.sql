select
    account_id,
    company_name,
    domain,
    industry,
    employee_count,
    region,
    tech_stack,
    customer_status,
    account_tags,
    deal_stage,
    assigned_ae_id,
    created_at
from {{ source('bronze', 'accounts') }}
