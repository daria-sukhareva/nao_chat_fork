# Retrospective: second blind sheet

**Date:** 2026-11-27
**Scope:** the author's ratings of the second blind sheet
(`judge_validation/rating_sheet_2026-11-25.md`) against three judges: long references, short
references, and short references with facts.
**Status:** facts dropped; the long-reference judge chosen for the confirmatory run; its fit to be
checked on a third blind sheet.

This follows the [2026-11-24 retrospective](retrospective_2026-11-24.md).

---

## Results

20 answers the author hadn't rated, cases q019 to q031, 10 from A and 10 from B, rated blind.
Correctness against the author:

| Judge                      | Same band (bar 70%) | Within 0.2 | Mean absolute difference | Judge minus author | Arm bias, B − A | Rank correlation | 0.9 or above (author: 12) |
| -------------------------- | ------------------- | ---------- | ------------------------ | ------------------ | --------------- | ---------------- | ------------------------- |
| Long references            | 7                   | 11         | 0.25                     | −0.11              | −0.11           | 0.70             | 3                         |
| Short references           | 6                   | 13         | 0.25                     | −0.04              | −0.11           | 0.42             | 5                         |
| Short references and facts | 4                   | 6          | 0.33                     | −0.19              | −0.12           | 0.57             | 0                         |

Over both sheets (40 answers; R17 at its blind score): same band 14, 13 and 10; rank correlation
0.62, 0.41 and 0.52; arm bias −0.10, −0.07 and −0.09. Completeness over both sheets: same band 18,
14 and 17; arm bias +0.03, +0.07 and +0.07.

**The facts judge failed.** It capped clean answers at 0.5 to 0.7, and its reasons do what the
rubric says not to: they penalise claims the facts don't mention ("not supported by the context",
S18), omissions ("misses the key nuance", S07), and contradictions that aren't there (S13,
"accidentally correct in number but wrong in reasoning"). It noticed S19's false "replacement" claim
but scored it 0.6, where the author gave 0.

**No judge reaches the same-band bar.** The author's scores sit at the ends of the scale (12 at 0.9
or above, 5 at 0.2 or below); the judge's sit in the middle. A gap of 0.2 across a band edge counts
as a miss (S04: author 1.0, facts judge 0.8).

**Arm bias is negative for every judge,** about −0.11 on this sheet: the judge scores B's answers
lower than the author does, relative to A's. That works against the hypothesis, and is reported.

## Decisions

1. Drop facts. The `facts` field stays in the code, but cases don't carry it and the rubric no
   longer reads it.
2. Use the long-reference judge: the full verified references (dataset of `d2ae4092c`, with q025's
   "no driver was recorded") and rubric `fbda3f9f0f46`, the pair the dev pilot ran with. It ranked
   answers most like the author on both sheets, so the choice doesn't rest on one sheet. It
   reverses the short-reference decision of 2026-11-24.
3. Check fit on a third blind sheet of confirmatory answers, with a bar fixed before it is drawn:
   rank correlation of at least 0.5 and arm bias within ±0.1 (experiment plan, Phase 4). Both
   sheets so far shaped the choice, so neither can test it.

The facts-source decision of 2026-11-26 ([2026-11-24 retrospective](retrospective_2026-11-24.md))
still holds, now for the references: the cause from the scenario, every number from the warehouse.

S06 (q027): the author notes the synthetic data allowed other readings, so it is a dataset problem
for q027, not a judge problem; all three judges agreed with the author.
