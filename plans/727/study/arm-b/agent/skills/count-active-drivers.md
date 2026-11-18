---
name: count-active-drivers
description: Calculate active drivers for any period and split them into new, returning, and approximate anonymous drivers. Owns the monthly_active_drivers, new_drivers, returning_drivers, anonymous_drivers, and visits_per_driver calculations in the metrics tree. Use whenever an answer counts drivers, including new or returning drivers, splits visits into drivers × visits per driver, or compares driver counts between periods, and when a visit-success change may be explained by the driver mix. Do not use for visit outcome definitions (use the semantic layer).
---

# count-active-drivers

**active_drivers = new_drivers + returning_drivers + anonymous_drivers**

New and returning are distinct credentials. Anonymous is an approximation: anonymous visits have no identity, so each one counts as one driver. These are query-derived results, not published semantic layer metrics, so label them that way.

## What already exists (read before querying)

| Location                                                                                                      | What's in it                                | Implication                                                                |
| ------------------------------------------------------------------------------------------------------------- | ------------------------------------------- | -------------------------------------------------------------------------- |
| `repos/kwwhat/models/semantic/semantic_models.yml`                                                            | Governed metrics, including `total_visits`. | Use `total_visits` and visit outcomes as defined. Don't recreate them.     |
| `repos/kwwhat/models/marts/marts.yml`                                                                         | Columns of `fact_visits`, `dim_drivers`.    | `first_seen_ts` is the driver's earliest visit end (needs kwwhat PR #192). |
| [`agent/skills/count-active-drivers/references/validation.md`](count-active-drivers/references/validation.md) | Boundary cases and pre-report checks.       | Go through it before reporting.                                            |

## Definitions

For a period [S, E), inclusive S and exclusive E, take the visits with `visit_end_ts` in the period:

| Metric              | Definition                                                   |
| ------------------- | ------------------------------------------------------------ |
| `new_drivers`       | Distinct known drivers whose first visit ended in the period |
| `returning_drivers` | Distinct known drivers whose first visit ended before S      |
| `anonymous_drivers` | Count of visits by the `UNKNOWN` driver                      |
| `active_drivers`    | Sum of the three above                                       |
| `visits_per_driver` | `total_visits` ÷ `active_drivers`, with the same period      |

A known driver has `dim_drivers.is_known_driver` true. Failed and successful visits both count.

`fact_visits` has already credited an anonymous attempt to the driver who authorized on the same port within 2 minutes, so those drivers aren't counted twice.

## Flow

### Step 1 — Fix the period

Resolve concrete timestamps S and E and validate S < E. Capture the clock once for relative periods. State the timezone and clarify ambiguity; never invent a conversion. Use validated timestamps, never arbitrary user SQL expressions.

Processing has a **35-minute SLA**. "Last two hours" literally means [clock − 120 min, clock), with the latest 35 minutes provisional. "Latest fully processed two hours" means [clock − 155 min, clock − 35 min). Never silently shift the requested window; state the endpoints instead.

### Step 2 — Run the split

Start from this query. Change only the rows of `periods` and any filters.

- Give each period its own row, with exactly one `period_start` and one `period_end`. New and returning are judged against that row's `period_start`, so a comparison of two periods is two rows in one query, never one window grouped by week or day.
- Apply a location or charger filter to the visits, but keep `first_seen_ts` network-wide: new means new to the network unless the user explicitly asks otherwise.

```sql
with periods as (
    select * from (values
        ('September 2025', timestamp '2025-09-01 00:00:00', timestamp '2025-10-01 00:00:00'),
        ('October 2025', timestamp '2025-10-01 00:00:00', timestamp '2025-11-01 00:00:00')
    ) as t (period_label, period_start, period_end)
)

select
    p.period_label,
    p.period_start,
    p.period_end,
    count(v.visit_id) as total_visits,
    count(distinct case when d.is_known_driver and d.first_seen_ts >= p.period_start then v.driver_key end) as new_count,
    count(distinct case when d.is_known_driver and d.first_seen_ts < p.period_start then v.driver_key end) as returning_count,
    count(case when not d.is_known_driver then v.visit_id end) as anonymous_count
from periods as p
left join analytics.MARTS.fact_visits as v
    on v.visit_end_ts >= p.period_start
    and v.visit_end_ts < p.period_end
    -- and v.location_id = '<location_id>'
left join analytics.MARTS.dim_drivers as d
    on v.driver_key = d.driver_key
group by p.period_label, p.period_start, p.period_end
order by p.period_start
```

### Step 3 — State the history coverage

New means first observed in the available history, so truncated history makes old drivers look new. Check where the history starts (the earliest `visit_end_ts` in `fact_visits`) and say so in any split: a driver counted as new in the first weeks of the data may have charged before it began.

### Step 4 — Explain a visit-success change (only if asked)

Join `dim_drivers` to the period's visits on `driver_key` and label each visit as new, returning, or anonymous using the rules above, so all of a driver's visits share one group.

- Preserve `is_successful` and the semantic definitions. Don't recreate the energy or status thresholds.
- Weight by **visits**, not drivers: expected success = Σ (current group visit share × matched baseline group success rate). Recompute groups for the baseline's own S.
- Label recent outcomes provisional and don't count ongoing visits as failed. `fact_visits` has no finalized flag, and the SLA doesn't prove a visit is complete.
- Report this as association, not cause, with sample sizes.

### Step 5 — Report

Follow the project's metrics-at-a-glance format. State S, E, timezone, and any history or processing caveats. Show anonymous as **≈**, with its share of active drivers. No visits means zero drivers, undefined shares, and an undefined success rate, not zero.

## Guardrails

- **Don't sum distinct counts across sub-periods or segments.** A driver active in two hours or at two locations is one driver for the whole. Recompute for the larger scope. Only `anonymous_drivers` is additive.
- **Assign each driver one group for the whole period.** Slicing a period into hours keeps the original S.
- **Treat anonymous as an upper bound.** One person with several anonymous visits counts several times, as does one who moves ports, since that starts a new visit. A person who authenticates more than 2 minutes after a failed anonymous plug-in counts as both anonymous and known.
- **Check the mix before reading a change as demand.** A shift from authenticated to anonymous starts raises `active_drivers` and lowers `visits_per_driver` with no change in real demand. Compare new + returning on its own.
- **Don't count `UNKNOWN` as one driver.**
