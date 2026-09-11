-- fct_subscriptions: cleaned subscription facts. Silver layer (view).

with source as (

    select * from {{ source('raw', 'raw_subscriptions') }}

)

select
    subscription_id,
    user_id,
    plan_tier,
    cast(mrr_amount as decimal(10,2)) as mrr_amount,  -- enforce money type
    currency,
    status,
    cast(started_at as date)  as started_at,
    cast(canceled_at as date) as canceled_at
from source