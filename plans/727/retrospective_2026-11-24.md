# Retrospective: shorter references

**Date:** 2026-11-24
**Scope:** the 13 dev references (q019–q031) shortened to a main claim, a supporting number and the
traps; the pilot's A, B and D answers rejudged against them.
**Status:** references changed in `golden_dataset.jsonl`, not yet committed. The rejudge is running
on copies of the pilot results in `demo/chat-bi/tests/outputs/short_refs_20261124/`; no results
yet.

This follows the [2026-11-23 retrospective](retrospective_2026-11-23.md).

---

## Why we decided to try

The worry: references carry so much detail that they penalise Correctness. The rubric doesn't
penalise omissions ("A required element that is missing is judged by Completeness, not here"), so
a long reference doesn't cost an answer for leaving things out. It costs it in two other ways:

- **More to contradict.** Every incidental detail is something an answer can contradict. q019 is
  the example: D's trial 2 named the `failure_reason` labels from kwwhat #204 (`INVALID_STOP_REASON`,
  `FAULTED_AFTER`), the reference named only the WeakSignal error, and the judge scored 0.3 for two
  descriptions of the same attempts.
- **More numbers to misread.** The judge's main error in the pilot was reading two different
  counts as one (q030 B in every trial, q025, q026, q023). References with several counts per
  case give it more chances.

## What we decided against, and why

**References cut to a claim and a number.** The rubric also says "Do not penalize claims the
expected output neither supports nor contradicts". Against a reference that holds only the main
claim, the errors the study tracks would score clean:

- q023's "12 ports", present-day topology applied to a past period;
- q027's "ports 2 inactive", an invented reliability cause;
- q031's "recovered", the check that runs and the conclusion that ignores it.

None contradicts a bare claim and number. The tree's supposed value is avoiding exactly those
errors, so a bare reference would make Correctness less sensitive to B against A, the primary
comparison. Completeness would reach its ceiling too.

**Changing references without measuring it.** The new style is only better if it scores answers
more like a person would, so it gets tested on answers already scored before it is adopted.

## What we did instead

Each reference keeps three things:

1. the main claim first;
2. the one number that supports it;
3. the case's misleading reading and data limits, stated as negations the judge can score against.

Incidental detail moved to the case's `notes`, which the judge doesn't see, with the full old
reference under a dated 2026-11-24 entry, so nothing is lost.

To test it without new agent runs: `nao evals rejudge` scores the `expected_output` stored in each
results file, so the 39 pilot files (A and B, 3 trials each on 13 cases, from 7936f876 and
ccc161aa; D, 2 trials each, from `5dda7a2c-dirty`) were copied with the short references swapped
in and rejudged once each, 104 answers for about $1.70. The originals are untouched.

The comparison, long against short:

- per-trial scores and arm means;
- B − A and D − A, with SD and SE, and the within-case SD that feeds the sizing;
- the judge's reasons on the known misreads (q030 B, q026 A), on the inventions that must stay
  penalised (q023, q027, q031) and on q019's D trial.

The blind rating decides between the two styles: keep the one whose scores agree better with the
human ratings. The choice goes into the case-generation rule before the preregistration tag.

## Main kinds of cut

- **Exact times and secondary counts:** q022's last visit at 20:38; q023's port-minutes; q026's
  port-minutes, 2,880 a day to 8,640; q029's per-location rates.
- **#204 labels and stop-reason names:** q019's `INVALID_STOP_REASON` and `FAULTED_AFTER`;
  DeAuthorized on q029 and q031.
- **Decompositions:** q027's split of the drop, about 80% fewer drivers and the rest fewer visits per
  driver; q030's 68 to 82 drivers and 2.1 to 1.8 visits per driver when anonymous visits are counted
  as drivers.
- **Second counts the judge has misread:** "10 known drivers" on q025; "6 of the 7 drivers" on q029
  and q030.

One phrasing changed rather than shrank: q019's "against 31 of 31 on its other days" became
"against none on its other days", the same claim with one fewer number.

## Kept as negations the judge can score against

- "This is new supply, not LOC-001 recovering" (q024), and "not LOC-001's demand recovering or
  falling" (q028);
- "new supply bringing new drivers, not returning demand" (q025);
- "not because of a reliability problem", with every visit succeeding and uptime above 99.6% (q027);
- "counting them as drivers would wrongly show more drivers" (q030);
- "the cause of the drop continues" and "isn't a trend" (q031);
- "CH-002 and its 2 ports were all that was commissioned" (q023), against the "12 ports" error;
- the data limits: "demand in those days can't be measured" (q022), "the data doesn't show why"
  (q020, q027), "too few to say anything about churn" (q021), "the data can't tie them to a driver"
  (q029).

## Still open

- The rejudge results and the long against short comparison.
- The blind rating, which picks the reference style.
- Rebuild each arm before the next eval run: the arms carry the dataset, and its hash changed.
