-- daily_active_users (DAU): distinct active users per calendar day.
-- Gold layer. Built from the silver stg_events model via ref().

with events as (

    select * from {{ ref('stg_events') }}

)

select
    cast(event_ts as date)          as activity_date,
    count(distinct user_id)         as dau
from events
group by cast(event_ts as date)
order by activity_date