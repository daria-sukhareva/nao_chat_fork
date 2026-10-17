# Metrics Tree: Successful Visits (original)

Original, untrimmed tree. The version used for the experiment, limited to metrics
defined in the semantic model, is [metrics_tree.md](metrics_tree.md).

---

# Successful visits (confirmed WoW drop)

- **Segments: location → charger → port**
  ΔSuccessful visits = Σ_segment ΔSuccessful visits_segment (exact, additive)
    - Concentration check: share of the drop explained by the top N segments
        - Concentrated → drill into the top contributors (tree below, per segment)
        - Diffuse → cross-cutting dimensions: auth type, CSMS / OCPP version, charger model, firmware

    - **Per segment: Successful visits = # Visits × VSR**
      Δlog(Successful visits) = Δlog(# Visits) + Δlog(VSR)
        - **# Visits**
            - Authenticated visits = # Drivers × Visits per driver
                - # Drivers (new / returning)
                - Visits per driver
            - Unauthenticated visits

        - **VSR** = w_auth · VSR_auth + w_anon · VSR_anon (mix effect + rate effect)
            - **Authenticated VSR**
                - First attempt success rate (p₁)
                    - Why: first-attempt funnel (port usable → auth accepted → tx started → energy > 0.1 kWh → clean stop → no fault after)
                - Troubled success rate = (1 − p₁) × recovery rate
                    - Why the first attempt failed (same funnel)
                    - Why recovery worked or not: retry rate, same vs. different port, retry success, alternative ports online
            - **Unauthenticated VSR**
                - First attempt success rate (p₁)
                    - Why: same funnel (free-vend or plug-and-charge start instead of auth)
                - Troubled success rate
                    - Why: same-port retries only (a different port starts a new visit)
