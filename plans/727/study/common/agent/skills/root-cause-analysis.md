---
name: root-cause-analysis
description: Investigate why a metric changed or what is driving it. Use for questions such as "why did X drop", "what caused this change", or "is this concentrated somewhere". Do not use for looking up a single value.
---

# root-cause-analysis

Work through these steps in order and report what each one found.

## 1. Confirm the change is real

Before explaining a change, check that the comparison is fair:

- **Data completeness:** both periods are complete. Check the data's actual coverage for each period, and look for late-arriving or missing data. If a period is partial, say so and compare on a matched basis, such as per day.
- **Calendar:** period length, holidays, and seasonality. Compare per-day rates when periods differ in length.
- **Definitions:** the metric's definition, thresholds, and the population it covers are the same in both periods, as far as you can tell.
- **Sample size:** the counts are large enough for the change to mean something. State the counts behind every rate.

If the change does not survive this step, say that and stop.

## 2. Split the metric into its parts

Write the metric as the components that combine to produce it, and compute how much each one contributed:

- **Multiplied parts:** use log contributions. `Δln(Y) = Σ Δln(xᵢ)`, and the share of part i is `Δln(xᵢ) / Δln(Y)`.
- **Added parts:** use absolute contributions. The share of part i is `Δxᵢ / ΔY`.

A rate moves only through its numerator and denominator: a lower count alone does not lower a rate.

## 3. Descend into the largest contributor

Split that contributor the same way. Repeat until you reach a part that cannot be split further.

## 4. Segment it

Split that part by the available dimensions, starting with location, then charger, port, and driver group. Report the share of the change in the top segments, and whether it is concentrated or spread out. When a location opens or closes inside the comparison, say so: the periods then cover different sites.

## 5. Separate mix from rate

A segment can move the total by changing its share rather than its rate: new low-performing segments can pull a total down while every existing segment stays flat. Report which one it is.

## 6. Check other explanations

Before concluding, check whether another part of the metric caused this movement. Many movements in one part come from a change in another.

## 7. Stay within the evidence

State only what the query results show. Treat a pattern as an association unless the data establishes the mechanism, and label any hypothesis as a hypothesis.

## 8. Report

- the conclusion first
- the path through the breakdown, with the contribution at each level
- the segment where the change concentrates
- the evidence: the queries and their results
- what is still unexplained, and your confidence
