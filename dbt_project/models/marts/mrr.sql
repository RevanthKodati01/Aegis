-- mrr: total Monthly Recurring Revenue from currently-active subscriptions.
-- Gold layer. Built from fct_subscriptions via ref().

with subs as (

    select * from {{ ref('fct_subscriptions') }}

)

select
    plan_tier,
    count(*)              as active_subscriptions,
    sum(mrr_amount)       as total_mrr
from subs
where status = 'active'          -- only count active (non-churned) subscriptions
group by plan_tier
order by plan_tier