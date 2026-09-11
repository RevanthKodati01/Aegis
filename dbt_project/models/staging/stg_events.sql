-- stg_events: cleaned, deduplicated events from raw_events.
-- Silver layer. Materialized as a view (per dbt_project.yml).

with source as (

    select * from {{ source('raw', 'raw_events') }}

),

deduplicated as (

    -- Remove duplicate event_ids, keeping one row per event_id.
    -- row_number() assigns 1,2,3... within each event_id group;
    -- we keep only row 1.
    select
        event_id,
        user_id,
        event_type,
        ts,
        properties,
        source,
        row_number() over (
            partition by event_id
            order by ts
        ) as rn
    from source

)

select
    event_id,
    user_id,
    event_type,
    cast(ts as timestamp) as event_ts,   -- ensure proper timestamp type 
    properties,
    source as event_source
from deduplicated
where rn = 1                              -- keep only the first row per event_id