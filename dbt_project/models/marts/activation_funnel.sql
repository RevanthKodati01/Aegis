-- activation_funnel: total count of each funnel stage across all events.
-- Gold layer. Shows the conversion story: many views -> few purchases.

with events as (

    select * from {{ ref('stg_events') }}

)

select
    event_type,
    count(*) as event_count
from events
group by event_type
order by event_count desc