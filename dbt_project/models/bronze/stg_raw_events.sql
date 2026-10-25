select
    event_id,
    event_type,
    event_source,
    contact_email,
    email_domain,
    ip_address,
    event_properties,
    occurred_at,
    ingested_at
from {{ source('bronze', 'raw_events') }}
