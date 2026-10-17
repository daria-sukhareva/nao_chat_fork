# metrics tree: successful charging visits

This file describes how the north star metric for an EV charging network decomposes into its drivers. Use it to do root cause analysis: when a metric moves, traverse the tree top-down, quantify how much each child contributed, descend into the biggest contributor, and repeat until you reach a leaf you can segment and explain.

Metric ids in `backticks` use the semantic layer's metric names where one exists. Ids without a semantic layer metric are logical names, marked TODO in the table at the end.

---

## 1. the tree

```
total_successful_visits                         [north star, monthly]
= total_visits × success_rate

total_visits                                    [demand vs capacity — comparison, not a product]
├── demand
│   = monthly_active_drivers × visits_per_driver
│   └── monthly_active_drivers = new_drivers + retained_drivers + resurrected_drivers
└── supply: free_port_minutes
    = total_commissioned_minutes × uptime_ratio × availability

success_rate
= first_attempt_success_rate + troubled_success_rate
└── troubled_success_rate = try_again_rate + switch_charger_rate + call_support_rate

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

### charge attempt

One try to charge on a connector. It starts at the connector's `Preparing` StatusNotification, or at `StartTransaction` if there was no `Preparing`. It ends at `StopTransaction`, or at the connector's next status if no transaction started. An attempt does not need a transaction: a plug-in that never starts one (authorization rejected, connector lock failure) is still an attempt.

### visit

Consecutive charge attempts by one driver at one location, where each attempt starts within a time window of the previous one's stop.

- **Authenticated** (idTag present): same location and idTag, gap ≤ 30 minutes. The driver can move between chargers and ports and stay in the same visit.
- **Unauthenticated** (no idTag): same charger and port, gap ≤ 2 minutes. Moving to another port starts a new visit.

An attempt without an idTag inherits one from an attempt on the same port within 2 minutes, so a failed plug-in followed by a successful authorized one is one authenticated visit. Every visit has at least one attempt. All unauthenticated visits share one `UNKNOWN` driver.

### successful visit

The visit's **last** charge attempt was successful. A successful attempt meets all of these:

- a transaction exists;
- it stopped with reason `Local`, `Remote` or `EVDisconnected`;
- energy transferred is more than 0.1 kWh (`success_energy_threshold_kwh`);
- the connector's next status is not `Faulted`.

Any other stop reason (`PowerLoss`, `EmergencyStop`, `Other`, ...) makes the attempt failed. A visit is failed when its last attempt failed, even if an earlier attempt succeeded.

### first_attempt_success_rate

Successful visits with exactly one charge attempt ÷ visits.

### troubled_success_rate

Successful visits with more than one charge attempt ÷ visits. The failed attempts can be on the same or another port, and do not have to come before a success: a visit counts if its last attempt succeeded.

Not computed in the data yet: each troubled visit would be credited to exactly one intervention, the last one before the successful attempt.

| intervention     | signal                                                                                                                                                                                                           |
| ---------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `try_again`      | successful attempt on the same port as the failed attempt                                                                                                                                                        |
| `switch_charger` | successful attempt on a different charger or port at the same location; only observable in authenticated visits, since an unauthenticated driver who switches ports starts a new visit                           |
| `call_support`   | CSMS-initiated action inside the visit window before the success: `RemoteStartTransaction` (1.6) / `RequestStartTransaction` (2.x), `Reset`, `UnlockConnector`, `ChangeAvailability`; or a linked support ticket |

Precedence: if a support action happened between the last failure and the success, credit `call_support`, even if the success came on the same port.

### monthly_active_drivers (MAD)

Distinct drivers with at least one visit in the month. A driver is an idTag, so only authenticated visits are counted per driver; unauthenticated visits all belong to the single `UNKNOWN` driver and are excluded.

- `new_drivers`: first visit ever is this month
- `retained_drivers`: visited this month and last month
- `resurrected_drivers`: visited this month, not last month, but at some point before

### visits_per_driver

Authenticated visits ÷ MAD.

### total_commissioned_minutes

Sum over ports of the minutes each port was commissioned during the month. A port commissioned mid-month contributes only its commissioned minutes.

### uptime_ratio

(commissioned minutes − outage minutes) ÷ commissioned minutes, summed over ports and days, so longer-commissioned ports weigh more. An outage is either:

- **FAULTED**: every connector of the port reports `Faulted`, or connector 0 (the whole charger) does;
- **OFFLINE**: the charger sends no messages for longer than the heartbeat interval (300 s).

`Unavailable` does not count as down. Uptime is status-based: it does not check whether charge attempts actually succeed.

### availability

Minutes not utilized ÷ minutes up. "Utilized" means a transaction is open on the connector, whether energy is flowing or not. A car that has finished charging but is still plugged in counts as utilized.

### free_port_minutes

`total_commissioned_minutes × uptime_ratio × availability`: minutes when a port was up and free for a new driver.

---

## 3. root cause procedure

1. **Confirm the change is real.** Before decomposing, check:
    - Data completeness: late-arriving transactions, CSMS outages, missing StatusNotifications, an open month.
    - Calendar: month length (compare per-day rates), holidays, seasonality (compare the same month last year), weather.
    - Definitions: any change to visit grouping (the 30- and 2-minute windows), the 0.1 kWh success threshold or port inventory.
2. **Split the north star.** Compute the log contributions of `total_visits` and `success_rate`.
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

`total_visits` is where demand meets capacity. Compare the two sides to find which constraint is binding at a site:

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
- **uptime_ratio ↔ first_attempt_success_rate.** Uptime is status-based. A port that is neither faulted nor offline but fails charge attempts keeps uptime flat while first_attempt_success_rate drops. If first_attempt_success_rate falls with stable uptime, look for per-charger failure concentration.
- **availability → switch_charger_rate.** Switching only works when a co-located port is free. Low availability suppresses this recovery path and turns would-be troubled successes into failures.
- **load management → availability.** Splitting power across ports (`SetChargingProfile`) lengthens charge attempts, so ports stay utilized longer.
- **failed visits → MAD.** Drivers whose visit failed are less likely to come back. A drop in success_rate shows up later as lower retained_drivers.
- **first_attempt vs troubled.** If first_attempt_success_rate falls and troubled_success_rate rises by the same amount, success_rate is flat but friction is rising. Always report both.
- **unobserved demand.** Drivers turned away from a full site produce no OCPP events, so observed demand under-counts true demand exactly when capacity binds.

---

## 6. guardrails

Check these when the north star improves, to make sure it isn't being gamed:

- `energy_per_successful_visit`: attempts just above the 0.1 kWh success threshold can inflate successful visit counts
- `cost_per_support_recovered_visit`: call_support is the most expensive recovery path
- `return_rate_after_failed_visit`: share of drivers with a failed visit who return within 30 days

---

## 7. semantic layer mapping

| logical id                   | semantic layer metric        | notes                                                                                                                                                                                                                                                                                                 |
| ---------------------------- | ---------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `total_successful_visits`    | `total_successful_visits`    | Equals `first_attempt_success` + `troubled_success`.                                                                                                                                                                                                                                                  |
| `total_visits`               | `total_visits`               | Every visit has at least one charge attempt, so all visits are attempted visits.                                                                                                                                                                                                                      |
| `success_rate`               | 1 − `failed_rate`            | No single metric. Equals `first_attempt_success_rate` + `troubled_success_rate`.                                                                                                                                                                                                                      |
| `first_attempt_success_rate` | `first_attempt_success_rate` |                                                                                                                                                                                                                                                                                                       |
| `troubled_success_rate`      | `troubled_success_rate`      |                                                                                                                                                                                                                                                                                                       |
| `failed_rate`                | `failed_rate`                |                                                                                                                                                                                                                                                                                                       |
| `try_again_rate`             | TODO                         | Needs first vs. last port of the visit; `fact_visits` has `first_port_id`/`last_port_id`, but only `first_charger_id`/`last_charger_id` are dimensions.                                                                                                                                               |
| `switch_charger_rate`        | TODO                         | Partly observable as troubled visits with `first_charger_id` ≠ `last_charger_id`; misses port switches on the same charger.                                                                                                                                                                           |
| `call_support_rate`          | TODO                         | No CSMS-initiated commands or support tickets in the semantic layer.                                                                                                                                                                                                                                  |
| `monthly_active_drivers`     | TODO                         | No distinct-driver count over visits. `drivers_count`/`known_drivers_count` count the driver dimension, not active drivers in a period.                                                                                                                                                               |
| `new_drivers`                | TODO                         | Approximated by `known_drivers_count` grouped by `drivers.first_seen_ts` month.                                                                                                                                                                                                                       |
| `retained_drivers`           | TODO                         |                                                                                                                                                                                                                                                                                                       |
| `resurrected_drivers`        | TODO                         |                                                                                                                                                                                                                                                                                                       |
| `visits_per_driver`          | TODO                         | Depends on `monthly_active_drivers`.                                                                                                                                                                                                                                                                  |
| `total_commissioned_minutes` | `total_commissioned_minutes` |                                                                                                                                                                                                                                                                                                       |
| `uptime_ratio`               | `uptime_ratio`               | `total_uptime_minutes` ÷ `total_commissioned_minutes`, so `total_commissioned_minutes × uptime_ratio` = `total_uptime_minutes` exactly. Drill down with `total_downtime_minutes` (by port, charger, location, date) and `total_downtime_minutes_detailed` (by `downtime_type`, `reason`, error code). |
| `availability`               | TODO                         | No utilization (open transaction minutes) in the semantic layer.                                                                                                                                                                                                                                      |
| `free_port_minutes`          | TODO                         | Depends on `total_commissioned_minutes` and `availability`.                                                                                                                                                                                                                                           |
