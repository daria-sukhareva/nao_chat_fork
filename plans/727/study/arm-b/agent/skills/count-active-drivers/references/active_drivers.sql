-- DuckDB sample. Replace the illustrative bounds with validated timestamps.
with parameters as (
    select
        cast('2025-10-01 00:00:00' as timestamp) as period_start,
        cast('2025-11-01 00:00:00' as timestamp) as period_end,
)

select
    p.period_start,
    p.period_end,
    count(distinct case when d.is_known_driver and d.first_seen_ts >= p.period_start then v.driver_key end) as new_count,
    count(distinct case when d.is_known_driver and d.first_seen_ts < p.period_start then v.driver_key end) as returning_count,
    count(case when not d.is_known_driver then v.visit_id end) as anonymous_count,
from parameters as p
left join analytics.MARTS.fact_visits as v
    on v.visit_end_ts >= p.period_start
    and v.visit_end_ts < p.period_end
left join analytics.MARTS.dim_drivers as d
    on v.driver_key = d.driver_key
group by p.period_start, p.period_end
