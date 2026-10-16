# metrics tree: successful charging visits

This file describes how the north star metric for an EV charging network decomposes into its drivers. Use it to do root cause analysis: when a metric moves, traverse the tree top-down, quantify how much each child contributed, descend into the biggest contributor, and repeat until you reach a leaf you can segment and explain.

Metric ids in `backticks` are logical names. Map them to the semantic layer in the table at the end.

---

## 1. the tree

```
successful_visits                               [north star, monthly]
= attempted_visits × success_rate

attempted_visits                                [demand vs capacity — comparison, not a product]
├── demand
│   = monthly_active_drivers × visits_per_driver
│   └── monthly_active_drivers = new_drivers + retained_drivers + resurrected_drivers
└── supply: free_port_minutes
    = deployed_port_minutes × uptime × availability

success_rate
= first_attempt_rate + troubled_rate
└── troubled_rate = try_again_rate + switch_charger_rate + call_support_rate

failed_rate = 1 − success_rate                  [complement, always report alongside]
```

### edge types

| symbol | meaning        | how to attribute a change                                                                |
| ------ | -------------- | ---------------------------------------------------------------------------------------- |
| `×`    | multiplicative | log contributions: `Δln(Y) = Σ Δln(xᵢ)`; share of child i = `Δln(xᵢ) / Δln(Y)`           |
| `+`    | additive       | absolute contributions: share of child i = `Δxᵢ / ΔY`                                    |
| `vs`   | comparison     | not decomposed arithmetically; read the ratio to find the binding constraint (section 4) |

Contributions under `×` and `+` should sum to the parent's change (within rounding). If they don't, the data has a definition mismatch. Flag it before going further.

---

## 2. definitions

### visit

A cluster of transactions and failed attempts by the same driver (idTag or vehicle) at the same location, within a 30-minute window between the end of one attempt and the start of the next. One visit can have several transactions.

### successful visit

The visit's final transaction delivered meaningful energy (MeterValues above a threshold, e.g. ≥ 1 kWh) and ended normally (e.g. `EVDisconnected`, `Local`, `Remote` after energy delivered). Transactions ending in `PowerLoss`, `EmergencyStop`, `Other` or a fault within the first few minutes are failed attempts.

### first_attempt_rate

Successful visits whose first transaction was successful ÷ attempted visits.

### troubled_rate

Successful visits that had at least one failed attempt before the successful transaction ÷ attempted visits. Each troubled visit is credited to exactly one intervention: the last one before the successful transaction.

| intervention     | signal                                                                                                                                                                                                           |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `try_again`      | successful transaction on the same EVSE/connector as the failed attempt                                                                                                                                          |
| `switch_charger` | successful transaction on a different charger/EVSE at the same location                                                                                                                                          |
| `call_support`   | CSMS-initiated action inside the visit window before the success: `RemoteStartTransaction` (1.6) / `RequestStartTransaction` (2.x), `Reset`, `UnlockConnector`, `ChangeAvailability`; or a linked support ticket |

Precedence: if a support action happened between the last failure and the success, credit `call_support`, even if the success came on the same port.

### monthly_active_drivers (MAD)

Distinct drivers with at least one attempted visit in the month.

- `new_drivers`: first visit ever is this month
- `retained_drivers`: visited this month and last month
- `resurrected_drivers`: visited this month, not last month, but at some point before

### visits_per_driver

Attempted visits ÷ MAD.

### deployed_port_minutes

Sum over ports of the minutes each port was commissioned during the month. A port deployed mid-month contributes only its deployed minutes.

### uptime

Minutes up ÷ minutes deployed. "Up" means the connector status is not `Faulted` or `Unavailable`, and the charger is connected to the CSMS. This is status-based. It does not check whether sessions actually succeed.

### availability

Minutes not utilized ÷ minutes up. "Utilized" means a transaction is open on the connector, whether energy is flowing or not. A car that has finished charging but is still plugged in counts as utilized.

### free_port_minutes

`deployed_port_minutes × uptime × availability`: minutes when a port was up and free for a new driver.

---

## 3. root cause procedure

1. **Confirm the change is real.** Before decomposing, check:
    - Data completeness: late-arriving transactions, CSMS outages, missing StatusNotifications, an open month.
    - Calendar: month length (compare per-day rates), holidays, seasonality (compare the same month last year), weather.
    - Definitions: any change to visit clustering, success threshold or port inventory.
2. **Split the north star.** Compute the log contributions of `attempted_visits` and `success_rate`.
3. **Descend into the largest contributor** and decompose it with the rule for its edge type. Repeat until you reach a leaf.
4. **Segment the leaf.** Useful dimensions: site, region, charger model, firmware version, connector type, power level, EV make/model, hour of week, site type (residential, workplace, public, highway), CSMS/network.
5. **Separate mix from rate.** A segment can move the total by changing its share, not its rate. Example: newly deployed sites with low uptime drag down network uptime while every existing site stays flat. Report which one it is.
6. **Check cross-branch couplings** (section 5) before concluding. Many leaf movements are caused by another branch.
7. **Report** in this structure:
    - path through the tree, with the contribution at each level
    - the leaf and segment where the change concentrates
    - the evidence (queries, OCPP signals)
    - what is still unexplained, and your confidence

---

## 4. reading demand vs supply

`attempted_visits` is where demand meets capacity. Compare the two sides to find which constraint is binding at a site:

| pattern                               | diagnosis                                                     | where to look                                                                   |
| ------------------------------------- | ------------------------------------------------------------- | ------------------------------------------------------------------------------- |
| low availability, flat or falling MAD | **capacity-constrained**: drivers queue or give up            | availability by hour of week, idle-occupied time, visits_per_driver at the site |
| high availability, growing MAD        | **siting or pricing problem**: ports are where drivers aren't | site-level visits vs nearby demand, price changes                               |
| high availability, falling MAD        | **demand problem**                                            | driver cohorts (new/retained/resurrected), competitor openings, price           |
| low uptime                            | **reliability problem**, which caps supply directly           | faults by charger model/firmware, connectivity                                  |

Monthly availability can hide peak saturation. A site can be 80% available over the month and fully occupied every evening. When availability looks healthy but drivers are leaving, check availability by hour of week.

---

## 5. cross-branch couplings

- **availability → visits_per_driver.** Saturated sites lose visits, often with a lag of one or more months as drivers move to other networks.
- **uptime ↔ first_attempt_rate.** Uptime is status-based. A charger that reports `Available` but fails sessions keeps uptime flat while first_attempt_rate drops. If first_attempt_rate falls with stable uptime, look for per-charger failure concentration.
- **availability → switch_charger_rate.** Switching only works when a co-located port is free. Low availability suppresses this recovery path and turns would-be troubled successes into failures.
- **load management → availability.** Splitting power across ports (`SetChargingProfile`) lengthens sessions, so ports stay utilized longer.
- **failed visits → MAD.** Drivers whose visit failed are less likely to come back. A drop in success_rate shows up later as lower retained_drivers.
- **first_attempt vs troubled.** If first_attempt_rate falls and troubled_rate rises by the same amount, success_rate is flat but friction is rising. Always report both.
- **unobserved demand.** Drivers turned away from a full site produce no OCPP events, so observed demand under-counts true demand exactly when capacity binds.

---

## 6. guardrails

Check these when the north star improves, to make sure it isn't being gamed:

- `energy_per_successful_visit`: very short sessions can inflate visit counts
- `cost_per_support_recovered_visit`: call_support is the most expensive recovery path
- `return_rate_after_failed_visit`: share of drivers with a failed visit who return within 30 days

---

## 7. semantic layer mapping

| logical id               | semantic layer metric | notes |
| ------------------------ | --------------------- | ----- |
| `successful_visits`      | TODO                  |       |
| `attempted_visits`       | TODO                  |       |
| `success_rate`           | TODO                  |       |
| `first_attempt_rate`     | TODO                  |       |
| `troubled_rate`          | TODO                  |       |
| `try_again_rate`         | TODO                  |       |
| `switch_charger_rate`    | TODO                  |       |
| `call_support_rate`      | TODO                  |       |
| `monthly_active_drivers` | TODO                  |       |
| `new_drivers`            | TODO                  |       |
| `retained_drivers`       | TODO                  |       |
| `resurrected_drivers`    | TODO                  |       |
| `visits_per_driver`      | TODO                  |       |
| `deployed_port_minutes`  | TODO                  |       |
| `uptime`                 | TODO                  |       |
| `availability`           | TODO                  |       |
| `free_port_minutes`      | TODO                  |       |
