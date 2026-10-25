select
    contact_id,
    account_id,
    email,
    first_name,
    last_name,
    title,
    seniority_level,
    department,
    contact_status,
    created_at
from {{ source('bronze', 'contacts') }}
