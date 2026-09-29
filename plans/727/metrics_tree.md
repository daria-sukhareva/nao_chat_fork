# Metrics Tree: Successful Visits

Treatment for the [experiment plan](experiment_plan.md) (arm B). Every node is a
metric, measure or dimension defined in `kwwhat/models/semantic/semantic_models.yml`,
so the tree does not conflict with the `RULES.md` rule "Do not make up metrics".

Not part of the demo context yet: it is added only for the treatment run.

---

## Successful visits (week-over-week drop)

`successful_visits_count` (visits measure) = `first_attempt_success` + `troubled_success`

- **Segments: location → charger (`last_charger_id`) → port**
  ΔSuccessful visits = Σ_segment ΔSuccessful visits_segment (exact, additive)
    - Concentration check: share of the drop explained by the top segments
        - Concentrated → drill into the top contributors (tree below, per segment)
        - Diffuse → slice by driver type (`drivers.is_known_driver`) and by error code
          (`last_error_code` → `error_codes`: taxonomy, fault code, description;
          `chargex_mrec_attributes`: responsible party)

    - **Per segment: successful visits = `total_visits` × (`first_attempt_success_rate` + `troubled_success_rate`)**
      Δlog(successful visits) = Δlog(`total_visits`) + Δlog(`first_attempt_success_rate` + `troubled_success_rate`)
      For segments with zero successful visits in either week, compare counts instead
      of logs.
        - **`total_visits`**
            - Slice by `drivers.is_known_driver` (known vs. unknown drivers)

        - **`first_attempt_success_rate`**
            - Slice by `drivers.is_known_driver`
            - Why: `last_error_code` of failed visits, decoded via `error_codes` and
              `chargex_mrec_attributes`
            - Port availability: `average_uptime`; `total_downtime_minutes` by reason
              (FAULTED by error code, OFFLINE)

        - **`troubled_success_rate`**
            - Slice by `drivers.is_known_driver`
            - Retry effort: `average_attempts_per_visit`
            - Why: `last_error_code` of troubled visits

        - **`failed_rate`** = 1 − `first_attempt_success_rate` − `troubled_success_rate`

---

## Removed from the original tree

Not defined in the semantic model:

- Visit success rate (VSR) as a named metric, and its mix/rate split between
  authenticated and unauthenticated visits (kept only as the `is_known_driver` slice).
- Recovery rate.
- Visits per driver; new vs. returning drivers.
- The first-attempt funnel (port usable → auth accepted → transaction started →
  energy > 0.1 kWh → clean stop → no fault after).
- Retry rate, same vs. different port retries, alternative ports online.
- Cross-cutting dimensions: auth type, CSMS / OCPP version, charger model, firmware,
  free-vend / plug-and-charge.
