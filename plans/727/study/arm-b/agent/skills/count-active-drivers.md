---
name: count-active-drivers
description: Calculate active drivers for any period and split them into new, returning, and approximate anonymous drivers. Owns the monthly_active_drivers, new_drivers, returning_drivers, anonymous_drivers, and visits_per_driver calculations in the metrics tree. Use when a question needs driver counts or the driver mix over a selected period, or when a visit-success change may be explained by that mix. Do not use for the published daily lifecycle stack (query `mad`, `mad_new`, `mad_retained`, `mad_resurrected` from the semantic layer) or for visit outcome definitions (use the semantic layer).
---

# count-active-drivers

**active_drivers = new_drivers + returning_drivers + anonymous_drivers**

New and returning are distinct credentials. Anonymous is an approximation: anonymous visits have no identity, so each one counts as one driver. These are query-derived results, not published semantic layer metrics, so label them that way.

## What already exists (read before querying)

| Location                                                                                                                | What's in it                                       | Implication                                                                |
| ----------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- | -------------------------------------------------------------------------- |
| `repos/kwwhat/models/semantic/semantic_models.yml`                                                                      | Governed metrics, including `total_visits`, `mad`. | Use `total_visits` and visit outcomes as defined. Don't recreate them.     |
| `repos/kwwhat/models/marts/marts.yml`                                                                                   | Columns of `fact_visits`, `dim_drivers`.           | `first_seen_ts` is the driver's earliest visit end (needs kwwhat PR #192). |
| [`agent/skills/count-active-drivers/references/active_drivers.sql`](count-active-drivers/references/active_drivers.sql) | DuckDB query for the full split.                   | Start from it. Change only the period bounds and any filters.              |
| [`agent/skills/count-active-drivers/references/validation.md`](count-active-drivers/references/validation.md)           | Boundary cases and pre-report checks.              | Go through it before reporting.                                            |

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

Adapt `agent/skills/count-active-drivers/references/active_drivers.sql`. Apply a location or charger filter to the visits, but keep `first_seen_ts` network-wide: new means new to the network unless the user explicitly asks otherwise.

### Step 3 — State the history coverage

New means first observed in the available history, so truncated history makes old drivers look new. The demo's 14-day seed cannot establish lifetime history, so disclose this in any split it produces.

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
- **Don't confuse this with `mad`.** `mad` excludes anonymous drivers and is a trailing 30-day daily snapshot; `mad_new` means first seen on that day, not in the period.
- **Don't count `UNKNOWN` as one driver.**
