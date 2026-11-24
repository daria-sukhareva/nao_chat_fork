# Retrospective: shorter references

**Date:** 2026-11-24
**Scope:** the 13 dev references (q019–q031) shortened to a main claim, a supporting number and the
traps; the pilot's A, B and D answers rejudged against them.
**Status:** short references adopted for the dev cases. All 104 pilot answers
rejudged against the short references (`demo/chat-bi/tests/outputs/short_refs_20261124/`, $1.36);
results below.

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

The plan was for the blind rating to decide between the two styles. That was dropped: see
Decisions.

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

## Results: long against short

Each of the 104 answers judged once against the short reference, compared with its original
judgment against the long one. Same answers, same judge, same rubric; only the reference changed.

| Correctness         | long  | short |
| ------------------- | ----- | ----- |
| A mean              | 0.63  | 0.65  |
| B mean              | 0.54  | 0.57  |
| D mean              | 0.42  | 0.50  |
| B − A (13 cases)    | −0.08 | −0.09 |
| SD of B − A by case | 0.19  | 0.12  |
| SE of B − A         | 0.054 | 0.033 |
| D − A               | −0.20 | −0.16 |
| Within-case SD, A+B | 0.21  | 0.25  |

| Completeness           | long  | short |
| ---------------------- | ----- | ----- |
| A mean                 | 0.48  | 0.64  |
| B mean                 | 0.49  | 0.62  |
| D mean                 | 0.29  | 0.43  |
| B − A                  | +0.01 | −0.02 |
| Trials at 0.9 or above | 9     | 35    |

- **Correctness barely moved, and B against A didn't change.** Means rose by 0.02 to 0.03 on A and
  B. B − A stayed at about −0.08. The spread of the per-case difference fell from 0.19 to 0.12, so
  its standard error fell from 0.054 to 0.033, while the trial-to-trial spread within a case rose
  from 0.21 to 0.25. On 13 cases neither is firm; the sizing isn't redone on it.
- **D gained most (+0.08), and D − A shrank from −0.20 to −0.16.** D's answers are terser, and the
  short references stopped penalising them for details they got differently. The positive control
  is slightly weaker under short references.
- **The traps still work.** q023's "12 ports" still scores 0.2 to 0.3 (A t1 and t2, both D trials):
  the judge quotes "CH-002 and its 2 ports were all that was commissioned" against it. q027 A t3's
  "only 2 of 8 connectors were active" still scores 0.1 against "not because of a reliability
  problem". q028 B t2 and the q031 "recovered" verdicts stay low.
- **"The data doesn't show why" now bites on q027 B.** All three B trials asserted a cause (an
  opening surge, then a trough) and fell from 0.6–0.7 to 0.5–0.6. The old reference had the same
  phrase; in a short one it is more prominent. That is the intended penalty: a cause the data
  doesn't support, stated as found.
- **Cutting a detail created a new misread on q023 B.** All three B trials fell (0.7, 0.7, 0.5 to
  0.4, 0.5, 0.4). They gave daily figures (Oct 15 at 33–50%, 0% on Oct 16–19) and a baseline over
  Oct 8–14 at about 100%, and the judge read each as contradicting the period figures (12.38% over
  Oct 15–19, 98.64% over Oct 1–14). The long reference had "uptime was 0% on each day from Oct 16
  to Oct 19", which told the judge the daily and period figures agree. Removing it made correct
  answers look wrong.
- **The q030 B misread survived.** B's answers say anonymous drivers who charged successfully were 0,
  which is true; the judge still reads it as contradicting "anonymous visits rose from 10 to 33". The
  scores rose (0.3, 0.3, 0.4 to 0.5, 0.5, 0.4), but the misread is the same.
- **q019 D t2 stayed low (0.3 to 0.4), and rightly.** The short reference no longer names the labels,
  but that trial called the cause "a backend/OCPP stop-reason issue", which contradicts "a fault on
  the charger". The old 0.3 wasn't only a label mismatch.
- **Completeness inflated.** 35 of 104 trials score 0.9 or above, against 9. With fewer points to
  cover, Completeness stops separating answers, and B − A on it is about zero either way.

**Reading.** Short references don't move the primary comparison, keep the traps, and may make the
per-case difference less noisy. They cost Completeness most of its range, and they create misreads
where a removed detail was what reconciled a correct answer stated at a different grain. The rule that follows: keep a detail when correct answers
commonly state the same fact another way (daily against period, per charger against network),
because without it the judge reads the other form as a contradiction.

**Decisions.**

- **Short references, chosen by the author rather than measured.** The primary comparison doesn't
  depend on the choice (B − A −0.08 long, −0.09 short), the traps work under both, and each style
  has a known cost: short references inflate Completeness and created the q023 B misread; long ones
  give the judge more to contradict and more counts to misread. A rating sheet of the answers where
  the two styles disagree (9 at a gap of 0.3 or more) would be too small to settle it. The style goes
  into the case-generation rule before the preregistration tag.
- **The blind rating keeps its original job:** checking that the judge is fit to score the
  references the study uses. The sheet (`judge_validation/rating_sheet_2026-11-23.md`, still blank)
  now shows the short references; the long version is in `5dda7a2c`. Its 20 answers were rejudged
  against the short references ($0.28), and the key holds both judgments, `judge_long` and
  `judge_short`.
- q023's short reference stays as it is, without the daily figure.
- Completeness stays as it is under short references, ceiling and all.

**Cost note.** The first rejudge attempt judged all 104 answers and saved none: it read the copies
through `/kwwhat`, which is mounted read-only in the container, and `rejudge` writes its output next
to the input file. That spent about $1.40, not in the cost ledger, which is written after the save.
The rerun used `/app/kwwhat/tests/outputs/...`, the same host folder mounted writable. Total for this
test: about $2.80. `rejudge` now checks that it can write the results folder and the ledger folder before the first
judgment, and stops if it can't.

## Still open

- The blind rating, against the short references.
- Rebuild each arm before the next eval run: the arms carry the dataset, and its hash changed.
