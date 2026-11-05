# Validation checklist

S is inclusive and E exclusive. A visit is in the period when its `visit_end_ts` is. `first_seen_ts` is the driver's earliest `visit_end_ts`.

## Boundary cases

| Case                 | History                                                     | Expected result           |
| -------------------- | ----------------------------------------------------------- | ------------------------- |
| First visit at S     | First visit ends exactly at S                               | New                       |
| First visit inside   | First visit ends between S and E                            | New                       |
| First visit spans S  | First attempt stops before S, first visit ends inside       | New                       |
| Earlier visit        | First visit ended before S, another visit ends inside       | Returning                 |
| Repeat visits        | Several visits in the period                                | One driver                |
| Visit ends at E      | `visit_end_ts` exactly E                                    | Not counted               |
| Visits before S only | No visit in the period                                      | Not counted               |
| Anonymous visit      | Visit with no `id_tag`, inside the period                   | One anonymous driver      |
| Two anonymous visits | Same person, two visits inside                              | Two anonymous drivers     |
| Inferred identity    | Anonymous attempt, authorized on same port within 2 minutes | Identified, not anonymous |
| Empty period         | No visits                                                   | Zeros; undefined shares   |

## Before reporting

- S < E, with the clock captured once for relative periods.
- `new_count` + `returning_count` + `anonymous_count` is at most `total_visits` for the same period and filters.
- History coverage is stated. Truncated history inflates new and deflates returning.
- Sub-period and segment counts were recomputed, not summed.
