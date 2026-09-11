-- dim_users: one clean row per user. Silver layer (view).

with source as (

    select * from {{ source('raw', 'raw_users') }}

),

deduplicated as (

    select
        user_id,
        signup_date,
        country,
        acquisition_channel,
        is_active,
        row_number() over (
            partition by user_id
            order by signup_date
        ) as rn
    from source

)

select
    user_id,
    cast(signup_date as date) as signup_date,
    country,
    acquisition_channel,
    is_active
from deduplicated
where rn = 1     -- guarantee one row per user (protects against duplicate-key faults)