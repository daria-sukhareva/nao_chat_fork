# Retrospective: why Correctness overlaps Completeness, and a new Correctness rubric

**Date:** 2026-11-07
**Scope:** tracing the Correctness/Completeness overlap from the first run with repetitions
back to the rubrics; the first live rejudge; and a new Correctness rubric.
**Status:** the rejudge of `evals_results_20261106_222427.json` finished
(`rejudge_results_20261107_222943.json`). The new Correctness rubric (`0015f7a322a7`, replacing
`c8b36757a66f`) is implemented, unit-tested (78 eval tests pass, lint clean), and checked
against the judge on five saved q018 answers. It has since been committed and is running in
`nao:study`. Completeness is unchanged (`c493b2deacb0`). The live check of `--arm-manifest`
found and fixed a gap (see
[Live check](#live-check-does---arm-manifest-stop-a-run-on-the-wrong-arm)).

This follows the [2026-11-06 retrospective](retrospective_2026-11-06.md), whose first live run
found the overlap.

---

## Context

In the first run with repetitions (q018, arm B), repetition 2 stated nothing false but left out
CH-001's 100% success rate and the words "mix shift". It scored Correctness 0.7 and Completeness
0.9, and the two judge reasons were nearly the same text. The question was whether the judge
misapplied the rubric or followed it.

It followed it. The overlap is written into the Correctness rubric.

---

## The Correctness rubric

From `cli/nao_core/commands/evals/correctness.py`:

```python
CORRECTNESS_RUBRIC = GEvalRubric(
    name="Correctness",
    evaluation_steps=[
        "Compare the actual output directly with the expected output for factual accuracy.",
        "Verify that every required fact, entity, value, and relationship is present and correctly represented.",
        "Verify that the required naming, terminology, and framing are used.",
        "Penalize contradictions, unsupported additions, and misleading details.",
    ],
    evaluation_params=["actual_output", "expected_output"],
)
```

The judge sees only the answer and the reference. It doesn't see the question or the tool
output. The default threshold is 0.5, and `GEvalRubric.version()` hashes the name, steps and
params into `rubric_version`.

Step by step:

| Step                                                            | What it checks                                             | Construct                                                                                             |
| --------------------------------------------------------------- | ---------------------------------------------------------- | ----------------------------------------------------------------------------------------------------- |
| 1. "…for factual accuracy"                                      | Whether what the answer says is true                       | **Correctness**                                                                                       |
| 2. "every required fact … is present and correctly represented" | "Present" is coverage; "correctly represented" is accuracy | **Completeness** and Correctness                                                                      |
| 3. "required naming, terminology, and framing"                  | Wording                                                    | **Neither.** It rewards matching the reference's words.                                               |
| 4a. "contradictions"                                            | Wrong claims                                               | **Correctness**                                                                                       |
| 4b. "unsupported additions"                                     | Extra claims                                               | Conflicts with the plan, which says extra claims that don't contradict the reference aren't penalized |
| 4c. "misleading details"                                        | Claims that are true but misleading                        | **Correctness**                                                                                       |

## The Completeness rubric, for comparison

From `cli/nao_core/commands/evals/completeness.py`:

```python
COMPLETENESS_RUBRIC = GEvalRubric(
    name="Completeness",
    evaluation_steps=[
        "Identify every distinct part of the question in the input and every required element of the expected output.",
        "Check whether the actual output addresses each part of the question and covers each required element.",
        "Heavily penalize omitted parts, partial answers, and answers that defer or deflect instead of answering.",
        "Do not penalize correct additional detail; judge only coverage, not wording or accuracy of extra content.",
    ],
    evaluation_params=["input", "actual_output", "expected_output"],
)
```

Completeness's step 2 and Correctness's step 2 both check that required elements are covered.
That shared step is the overlap the q018 run showed. Step 3 of Correctness explains the rest:
repetition 2 described the mechanism ("3 more drivers chose the faulty port") without the
reference's words ("mix shift"), and lost points for it.

## Two more gaps

- **Neither metric uses the "Must not claim" list explicitly.** The references have that
  section, but Correctness never mentions it. The judge only catches a violation through
  "contradictions" or "misleading details".
- **There are no score bands.** The plan calls for `evaluation_steps` plus GEval's `rubric`
  score bands, but only the steps are built. So the judge picks a score from 0 to 10 without
  anchors for what, say, 7 means. That's another reason a borderline answer can land on 0.7 or
  0.8.

---

## Why it matters

Correctness is the primary endpoint. As written, it partly measures coverage and wording, so a
Correctness effect of the tree can't be read apart from Completeness. Step 3 is the more
serious part for this study. If the metrics tree teaches the agent the reference's vocabulary,
arm B would score higher on Correctness for wording alone, which is the judgment contamination
the 2026-11-05 retrospective warned about, entering through the rubric instead of the reference.

## Decision recorded

[Open decision 4](experiment_plan.md#open-decisions) lists three options:

- **Separate the constructs (recommended).** Correctness keeps steps 1, 4a and 4c, adds an
  explicit "Must not claim" check, and drops steps 2, 3 and 4b. It also gets score bands.
  Completeness scores coverage of the "Required" list. How often the two disagree is reported
  as a check that they now measure different things.
- **Keep both as they are** and report them as overlapping.
- **Merge them** into one reference-based score, losing the split between wrong and missing.

Whichever is chosen changes `rubric_version`, so it has to be settled before any run that
counts. A matching bullet was added to Phase 4 in the plan.

## The rejudge result

`nao evals rejudge evals_results_20261106_222427.json --judge-repeats 3`, with the old rubric
(`c8b36757a66f`) and the original judge settings (temperature 0, max tokens 4096). Each row has
four judgments of the same text: the original one, then the three rejudges.

| Metric              | Answer 1 (rep 1)       | Answer 2 (rep 2)       | Spread within an answer | Gap between answers |
| ------------------- | ---------------------- | ---------------------- | ----------------------- | ------------------- |
| **Correctness**     | 1.0, 0.9, 0.9, 1.0     | 0.7, 0.7, 0.7, 0.7     | 0 to 0.1                | **0.2 to 0.3**      |
| Completeness        | 1.0, 1.0, 1.0, 1.0     | 0.9, 0.9, 0.9, 0.9     | 0                       | 0.1                 |
| Faithfulness        | 1.0, 1.0, 1.0, 0.91    | 1.0, 0.96, 0.95, 0.88  | **up to 0.13**          | about 0.05          |
| ContextualRelevancy | 0.65, 0.60, 0.65, 0.64 | 0.60, 0.65, 0.61, 0.70 | up to 0.10              | about 0             |
| AnswerRelevancy     | 0.93, 1.0, 1.0, 1.0    | 0.96, 0.96, 0.96, 1.0  | up to 0.07              | about 0             |

**The 1.0 versus 0.7 gap comes from the agent, not the judge.** Correctness is reproducible:
answer 2 got 0.7 four times, and answer 1 moved by one 0.1 step. The spread within an answer is
smaller than the gap between answers, so the judge can tell these two answers apart. As
predicted, the GEval scores moved in steps of 0.1 or not at all. Reproducible isn't right,
though: answer 2's 0.7 is the omission penalty described above, applied the same way every time.

**Faithfulness is noisy, and the judge made errors.** All three deductions on answer 2 claim
the answer got its dates wrong: that the 40% → 10% figures "actually occurred on 2025-10-01 and
2025-10-02", and that "no data for Oct 4's visit breakdown was provided". That's false. The
Oct 4 and Oct 5 rows are in at least five SQL results in the retrieval context, and the
SQL-checked reference agrees with the answer. Two things seem to have tripped the judge:

- **Repeated values.** The week's daily rates repeat (40, 10, 20, 40, 10), so Oct 1–2 look
  exactly like Oct 4–5.
- **A large context.** 50–97K characters per answer.

So:

- **The 2026-11-06 Faithfulness of 1.0 on answer 2 was luck.** Its four scores range from 0.88
  to 1.0 for the same text.
- **Faithfulness can't rank these two answers,** because its spread within an answer is larger
  than the gap between them.
- **Answer 1's one deduction is arguable.** It said "all week" and "100% uptime across all
  dates", generalizing beyond what it queried.

**ContextualRelevancy and AnswerRelevancy are noise here.** Each varies as much within an
answer as between answers.

What it means for the study:

1. **Correctness is reproducible enough to use,** once it measures the right construct (below).
2. **Faithfulness needs validation before it can be a secondary metric.** It's the only metric
   that made a factual error about the context, and the error went against a correct answer.
   Long contexts with repeated values are what root cause cases produce. Until it's validated
   against human labels, it's exploratory.
3. **H3 gets harder to test.** Proxies whose judge noise is as large as the differences between
   answers can't track Correctness. They'd need several judge repetitions per answer, averaged
   at analysis time, or they stay troubleshooting tools.
4. **The first live `rejudge` worked.** It produced six judgments, with no errors and nothing
   skipped. It recorded the source path and hash, the `run_id`, the rubric version and the judge
   settings. The judge's cost is still not recorded.

---

## The new Correctness rubric

Open decision 4's recommended option was implemented: Correctness judges only what the answer
claims.

```python
evaluation_steps=[
    "List the factual claims the actual output makes: values, entities, dates, relationships, and causes.",
    "Compare each claim with the expected output for factual accuracy, and penalize every claim that "
    "contradicts it.",
    "If the expected output lists claims the answer must not make (for example under 'Must not claim'), "
    "heavily penalize an actual output that makes any of them, in any wording.",
    "Penalize details that are accurate on their own but misleading in context.",
    "Do not penalize omissions. A required element that is missing is judged by Completeness, not here.",
    "Do not penalize wording. A fact or mechanism stated in different terms from the expected output is correct.",
    "Do not penalize claims the expected output neither supports nor contradicts.",
]
```

| Old step                                    | New rubric                                                                       |
| ------------------------------------------- | -------------------------------------------------------------------------------- |
| 1. Factual accuracy                         | Kept, split into listing the claims and comparing each one                       |
| 2. Every required fact is present           | Dropped; replaced by "Do not penalize omissions"                                 |
| 3. Required naming, terminology and framing | Dropped; replaced by "Do not penalize wording"                                   |
| 4a. Contradictions                          | Kept                                                                             |
| 4b. Unsupported additions                   | Dropped; replaced by "Do not penalize claims … neither supports nor contradicts" |
| 4c. Misleading details                      | Kept                                                                             |
| (none)                                      | New: the "Must not claim" check, conditional so prose references still work      |

The "do not penalize" steps are stated explicitly, not just left out. A judge told only what to
penalize still tends to mark down missing facts, which is what the old step 2 did.

Score bands, passed to GEval as its `rubric`:

| Score | Meaning                                                                                                                                                                   |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| 0–2   | The main conclusion contradicts the expected output, the output makes a claim it must not make, or it makes no substantive claim about what the expected output addresses |
| 3–5   | The main conclusion agrees, but a central value, entity, or cause is wrong, or several claims contradict it                                                               |
| 6–8   | The main conclusion and central claims agree; one or two minor claims are wrong or misleading                                                                             |
| 9–10  | No claim contradicts the expected output, and none is misleading                                                                                                          |

Design choices:

- **A guard against empty answers.** A rubric that only penalizes wrong claims gives full marks
  to an answer that says nothing, or one that deflects. The 0–2 band's last clause closes that
  gap without bringing back coverage: it asks whether the answer makes any claim about the
  subject, not whether it covers the required list.
- **A "Must not claim" item puts the answer in the 0–2 band.** These items are the case's trap,
  the wrong diagnosis the case exists to catch.
- **The judge still sees only the answer and the reference,** not the question or the tool
  output. Checking claims against the evidence is Faithfulness's job.
- **It stays generic.** Nothing in it mentions root cause analysis, the metrics tree, or EV
  charging. What a case requires stays in its reference.
- **The bands span 0–10 without gaps.** DeepEval normalizes the score over the bands' full
  range, so a gap or a shorter range would change what 0.7 means.
- **Versioning.** `GEvalRubric` gained `score_bands`, which are hashed into `rubric_version`
  only when present. So Completeness, which has no bands, keeps its old version, and its scores
  stay comparable with earlier runs.

Only q018 uses the "Required / Must not claim" format so far. The other 11 references are
prose, so for them the "Must not claim" step is inactive until they're rewritten.

**Expected effect on q018:** answer 2 stated nothing false, so it should move from 0.7 to 9–10.
If it doesn't, the "do not penalize omissions" step isn't working, and the reason will say why.
This was written as a prediction before the check. **It held:** answer 2 scored 0.9 in all three
judge repetitions (see below).

---

## Checking the new rubric against the judge

The new rubric was tried on five saved q018 answers, three judge repetitions each, with
`nao evals rejudge --metrics correctness`. All five answers use the current reference. It took
two runs, each testing a different way the rubric could fail:

| Run | Answers                                                           | Question                                                                 | Outcome                                                                                                       |
| --- | ----------------------------------------------------------------- | ------------------------------------------------------------------------ | ------------------------------------------------------------------------------------------------------------- |
| 1   | The two from 2026-11-06 22:24, both right about the cause         | Does it stop penalizing omissions and wording?                           | **Yes.** Repetition 2 rose from 0.7 to 0.9, three times out of three, and the gap between the answers closed. |
| 2   | Three from early 2026-11-06: one wrong, one borderline, one right | Does it still penalize wrong claims, or has it just become more lenient? | **It still catches the wrong answer** (0.2 three times). The borderline answer is unstable (0.5 to 0.8).      |

Run 1 alone couldn't tell a better rubric from a more lenient one, because a rubric that gave
every answer 0.9 would also pass it. Run 2 added a known wrong diagnosis to rule that out.

**How it was run.** The host has no judge API key, so the image wasn't rebuilt. Instead, the
two changed files (`rubric.py`, `correctness.py`) were copied into the running container's CLI
package, the rejudges were run, and the originals were copied back. The container was confirmed
to be on `c8b36757a66f` again before and after. Each rejudge file records `rubric_version`
`0015f7a322a7`, so its scores can't be mistaken for the old rubric's. This is fine for a check;
runs that count need the rebuilt image.

| Answer                          | What it says                                                  | Old rubric         | New rubric    |
| ------------------------------- | ------------------------------------------------------------- | ------------------ | ------------- |
| `20261106_014925`               | Wrong mechanism: the fault "got worse overnight", "escalated" | 0.2                | 0.2, 0.2, 0.2 |
| `20261106_020913`               | Right mechanism, but "the situation worsened on Oct 5"        | 0.6                | 0.8, 0.7, 0.5 |
| `20261106_022022`               | Right mechanism; leaves out CH-001's 100%                     | 0.7                | 0.8, 0.8, 0.8 |
| `20261106_222427`, repetition 2 | Right mechanism; leaves out CH-001 and the words "mix shift"  | 0.7, 0.7, 0.7, 0.7 | 0.9, 0.9, 0.9 |
| `20261106_222427`, repetition 1 | Right mechanism, complete                                     | 1.0, 0.9, 0.9, 1.0 | 0.9, 0.9, 0.9 |

Files: `rejudge_results_20261107_224017.json` (the two answers from 2026-11-06 22:24),
`_225209`, `_225235` and `_225255` for the other three, in that order.

**What worked:**

- **A wrong diagnosis is still caught.** The "escalating fault" answer scored 0.2 all three
  times, and every reason names the "Must not claim" violation. So the rubric didn't lose its
  ability to tell wrong answers apart. A rubric that gave everything 0.9 would have failed this.
- **Omissions and wording stopped crossing bands.** Repetition 2 of the 22:24 run moved from 0.7
  to 0.9. The judge said its gaps "are omissions rather than contradictions, so they are not
  penalized", and accepted "more drivers chose the faulty port" as the mix-shift mechanism.
- **The ranking now follows what the answers claim:** wrong (0.2), borderline (0.5–0.8), then
  right but incomplete (0.8–0.9).
- **Completeness now does the separating.** The two 22:24 answers tie on Correctness and differ
  on Completeness (1.0 versus 0.9), which is what separating the constructs means.

**What didn't:**

1. **The borderline answer is unstable: 0.8, 0.7, 0.5.** That's the largest judge spread seen so
   far on a GEval metric. The judge couldn't decide whether "the situation worsened on Oct 5"
   breaks the rule against claiming "that something new broke on Oct 5". Its reasons contradict
   themselves, saying the answer "makes a claim it must not make" and then that it "does not
   claim something new broke". Even when it decided there was a violation, it gave 0.5, not the
   0–2 the band requires. The cause is the reference: the success rate really did get worse on
   Oct 5, so "the situation worsened" is true. The item should forbid what's actually wrong,
   that a charger changed, along the lines of "That CH-002 or any charger got worse on Oct 5".
   That's the q018 tightening already on the list, now with evidence for it.
2. **Omissions still move scores within the top bands.** The 02:20 answer and repetition 2 of the
   22:24 answer leave out the same thing, CH-001's 100%, yet scored 0.8 and 0.9. Every
   high-scoring reason lists omissions, calls them unpenalized, and stops at 8 or 9 rather than 10. The leak is now within a band rather than across bands, which is much smaller, but it's
   still there.
3. **Two judge reasons say things the answer doesn't.** One says repetition 2 of the 22:24 run
   mentions CH-001's 100%; it doesn't. The scores didn't depend on it. Together with the
   Faithfulness date errors, that's two misreadings by the judge in one day.

**What this check is not.** It's five answers to one case, scored by a judge that is the same
model as the agent, read by the person who wrote the rubric. It shows the rubric does what it
was designed to do on these answers. It isn't scorer validation, which still needs agreement
with human labels across cases (Phase 4).

## Rule compliance: tested, then left out of scope

**Why it came up.** The old Correctness step 3, "the required naming, terminology, and framing",
was added to enforce a `RULES.md` rule: `Never use the term "session"`. Dropping it raised the
question of whether anything still enforces that rule.

**Why step 3 couldn't have.** The Correctness judge sees only the answer and the reference,
never `RULES.md`, and no reference mentions "session". So step 3 could only reward the
reference's own words. None of the saved answers uses "session", so dropping it hid no
violation.

**The test.** Answer 1 from the 2026-11-06 22:24 run was faked twice, and both fakes are
labeled `synthetic: true` in `tests/outputs/synthetic/session_term_20261107.json`:

- **Light:** one "visits" in the conclusion replaced with "sessions".
- **Heavy:** all 14 "visit"s replaced.

Each was scored three times on Correctness and Completeness under both rubrics.

| Answer                | Old Correctness    | New Correctness | Completeness (both rubrics) |
| --------------------- | ------------------ | --------------- | --------------------------- |
| Control: the original | 1.0, 0.9, 0.9, 1.0 | 0.9, 0.9, 0.9   | 1.0                         |
| Light: 1 "session"    | 0.9, 0.9, 0.9      | 0.9, 1.0, 0.9   | 1.0, every time             |
| Heavy: 14 "session"s  | 0.9, 0.9, 0.9      | 1.0, 1.0, 1.0   | 1.0, every time             |

Nothing caught it. Under the old rubric the judge wrote "volume stable at 10 sessions" in its
own reason and then said "the terminology and framing align well". The old step 3 never
enforced the rule.

**Faithfulness** was tested too, both as it runs today and with
`penalize_ambiguous_claims=True`. It's unlikely to catch the rule, for three reasons:

- `RULES.md` reaches the agent through the system prompt, not a tool, so it isn't in the
  judge's context.
- The only "session" in that context is in kwwhat's own dbt docs (`marts.yml`).
- Faithfulness checks claims against facts, and a rule is not a fact.

It didn't catch it. Strict mode was swapped into the container's `rag.py` for the test and
restored afterwards. Because strict mode might lower scores for reasons unrelated to "session",
the unmodified answer was scored in strict mode too, as a control:

| Answer                | Default Faithfulness | Strict Faithfulness |
| --------------------- | -------------------- | ------------------- |
| Control: the original | 1.0, 1.0, 1.0, 0.91  | 0.57, 0.70, 0.65    |
| Light: 1 "session"    | 0.96, 1.0, 0.96      | 0.57, 0.58, 0.63    |
| Heavy: 14 "session"s  | 0.96, 1.0, 0.96      | 0.65, 0.68, 0.68    |

- **Default Faithfulness doesn't see the word.** The fakes score in the control's range.
- **Strict mode's drop has nothing to do with "session".** The unmodified control falls just as
  far, and the light fake scored lower than the heavy one.

**What strict mode penalizes,** from the control's reasons:

- **Generalizing beyond what was queried.** "Failing 100% of its visits all week" and "all
  visits at LOC-001 across all dates", when the context confirms only Oct 4 and 5. That's a fair
  catch.
- **Domain explanation.** "The connector lock mechanism is unable to engage" is not stated in
  the context. That's arguably fair, too.
- **The correct conclusion, called a contradiction.** Two of three reasons say the mix-shift
  framing "contradicts" the context, because CH-002 was failing on both days. That's the judge
  misreading the diagnosis. The answer says the failure isn't new, and the context agrees.

So strict mode fails the best answer so far at the current 0.7 threshold (0.57 to 0.70). It
does so partly for real overgeneralizations and partly by misjudging the conclusion. The
plan's strict Faithfulness (`penalize_ambiguous_claims=True`, decided on 2026-11-05) was never
built into `rag.py`. This result means it shouldn't be, as planned, without validation: a
metric that marks the correct diagnosis as contradicted can't be a secondary endpoint on root
cause cases. Files: `rejudge_results_20261107_232843.json` (default) and `_235054` (strict) for
the fakes, and `rejudge_results_20261108_000233.json` (strict) for the control, all in
`synthetic/`.

**Considered: giving the judge the system prompt.** Rejected, for four reasons:

- It unblinds the judge, because arm B's prompt mentions the metrics tree.
- A rule isn't evidence that Faithfulness can check claims against.
- It adds 15 KB to contexts the judge already misreads.
- It would change what ContextualRelevancy means.

A curated, arm-neutral part could still serve two other purposes later:

- the rules, as a rule-compliance scorer's constraint list;
- the date and table list, as evidence for Faithfulness.

**Decision: rule compliance is out of scope for this study.** It's a different construct from
diagnostic quality and needs its own eval, which could mostly be deterministic: a word match for
banned terms, and table and introspection checks over the recorded SQL. The experiment plan
records it under settled decisions and out of scope. The whitepaper has to say that rule
compliance wasn't measured, so it can't claim the tree leaves rule following unchanged.

## Live check: does `--arm-manifest` stop a run on the wrong arm?

This is check 4 of Phase 0's live check (verification item 7 of the instrumentation plan). It
ran after `nao:study` and the demo were rebuilt from the eval code (`f0c0554c`) with arm B
served. A smoke run on B (`evals_results_20261108_020527.json`, q018 with 2 repeats) confirmed
the new image first:

- the arm manifest matched;
- the Correctness rubric was `0015f7a322a7`;
- the nao and study commits were clean;
- cost was recorded: $0.46 for the agent and $0.71 for the judge.

**Setup.** Arm A was built into a scratch directory outside the repos, so they stayed clean, and
its manifest was copied into the running B container:

```bash
~/github/nao_chat_fork/plans/727/study/build-arm.sh A ~/github/kwwhat/demo/chat-bi /tmp/armA
docker cp /tmp/armA.json "$(docker ps -qf name=chat-bi-run)":/tmp/armA.json
nao evals -s q018 --arm-manifest /tmp/armA.json   # inside the container
```

**First attempt: the run stopped, but for a weak reason.**

```
✗ The served project is not arm A as built in /tmp/armA.json:
  • RULES.md differs from the arm A build
Rebuild the demo image from the arm, or pass the manifest of the arm it was built from.
```

The run stopped before the first agent call, which is the behavior the check exists for. But
only `RULES.md` was reported. B serves four files A's manifest doesn't list: the metrics tree
and the three `count-active-drivers` files. The check only confirmed that each file in the
manifest was served with the right hash. It never asked whether something was served that the
manifest doesn't list. It caught this image only because B also appends a rule to `RULES.md`.

That matters because the tree leaking into A is the confound that would hide the effect the
study is measuring. Take an arm-A image that still serves `docs/metrics_tree.md`, from a stale
build or because the tree later lands in the kwwhat repo. If its `RULES.md` matched, it would
have passed as A.

**Fix (`20d1638b`).** The check now also reports every served file the manifest doesn't list.
It skips what every arm shares: files under `databases/` and `repos/`, and `nao_config.yaml`.

**Second attempt, after rebuilding `nao:study` from `8938426c` and the demo.** Both arms were
assembled before the q018 change. B was built at 20:46 and arm A's manifest at 21:10, while the
change was committed at 21:16.

```
✗ The served project is not arm A as built in /tmp/armA.json:
  • RULES.md differs from the arm A build
  • agent/skills/count-active-drivers.md is served but is not part of arm A
  • agent/skills/count-active-drivers/references/active_drivers.sql is served but is not part of arm A
  • agent/skills/count-active-drivers/references/validation.md is served but is not part of arm A
  • docs/metrics_tree.md is served but is not part of arm A
Rebuild the demo image from the arm, or pass the manifest of the arm it was built from.
```

The output is what was expected: the four B-only files are named, and the run still stopped
before any agent call, so it cost nothing. The dataset isn't reported because the image and
A's manifest held the same old dataset (`28b383b95ca2`). It doesn't show that the new q018
reference was served, and it wasn't.

## Live check: does `compare` accept a matched pair and refuse a changed one?

These are checks 5a and 5b, run in the same container as check 4. They still used the old q018
reference, because arm B hadn't been rebuilt, but that doesn't affect what they test.

**5a: two B runs (`024822` and `030000`, q018 with 2 repeats each), compared: passed.**

```
evals_results_20261108_030000.json: experiment None, arm B, block None
evals_results_20261108_024822.json: experiment None, arm B, block None
✓ 2 runs held everything fixed except the arm.
```

Both runs had the same nao commit (`8938426c`), context (`f35231563912`) and dataset
(`28b383b95ca2`), and neither changed during the run. No preview note appeared, because
`nao sync` ran once for both runs. Correctness was 1.0, 1.0 and 0.9, 1.0. The 0.9 was the judge
marking down "Oct 1–7 rather than Oct 1–14", the criterion that `8938426c` removes. The success
message is a fixed string, and it says "except the arm" even when the arm didn't vary.

**5b: a changed `RULES.md`: first accepted, then fixed.** A test line was appended to
`/app/kwwhat/RULES.md` in the container. With `--arm-manifest`, the run stopped because
`RULES.md` differed. Without the flag, it ran (`031312`), and its `RULES.md` and context hashes
differed from `024822`'s. Yet `compare` passed:

```
evals_results_20261108_024822.json: experiment None, arm B, block None
evals_results_20261108_031312.json: experiment None, arm None, block None
✓ 2 runs held everything fixed except the arm.
```

`compare` treated `B` and `None` as two different arms. Different arms may differ in their arms'
files, and B's manifest lists `RULES.md`, so the edit was accepted as part of arm B. Any run made
without `--arm-manifest` could have been paired this way, with any change to an arm file.

**Fix (`b5b96776`).** A run with no arm label is a problem, because nothing vouches for its
context. After rebuilding `nao:study`:

```
✗ These runs can't be paired (1 problem(s)):
  • evals_results_20261108_031312.json: no arm label, so its context can't be checked against an arm (run with --arm-manifest)
```

The branch for identical labels was checked offline, on a copy of `031312` labeled arm B with
`024822`'s manifest. It was refused for both reasons: "same arm B, but RULES.md differs" and
"same arm B, but the system prompt differs".

## Live check: does `--max-cost` stop a run?

`033339`: q018 with 2 repeats and `--max-cost 0.1`, below the cost of one trial.

```
Cost: $0.55 (agent $0.22, judge $0.33)
Stopped after 1 of 2 trial(s): max_cost.
✓ All 1 eval(s) passed
```

The first trial ran and the second didn't. The file records `trials_run: 1` and
`stopped: {"reason": "max_cost", "spent_usd": 0.5458, "max_usd": 0.1}`, and so does the
ledger line. The overshoot, $0.55 against a $0.10 cap, is the one trial that was already
running. That's by design: the limit is checked between trials. A one-trial run can therefore
never be stopped, which is why an earlier one-trial run under `--max-cost 1` finished at $0.53.
The final "✓ All 1 eval(s) passed" is misleading after a stop. It counts only the trials that
ran, even though the run exits 1.

## Live check: the new q018 reference is served

After arm B was rebuilt from `b5b96776` (dataset `2fb954ac8e71`), a clean B smoke run was
reported fine. Its results file hasn't been reviewed here.

## Live check: an A run paired with a B run

A q018 run on arm A, compared with the clean B run, was reported to pass. Its results files
haven't been reviewed here.

## Order of work

The new rubric was drafted only after the rejudge finished, so the old rubric's reproducibility
was measured first and there was a baseline to compare against. It was then checked on saved
answers with `nao evals rejudge --metrics correctness`, which needed no agent calls. The
answers included a known wrong diagnosis, so that a rubric that had become too lenient would
show it.

## Lessons

- **Read the rubric before blaming the judge.** The judge's reasons looked like a judging
  error. They were the rubric's own steps, applied faithfully.
- **Two answers to one case exposed what one answer couldn't.** With a single answer, a 0.7
  looks like a quality score. With a second, better-scored answer next to it, the difference
  could be traced to what each rubric step rewards.
- **Wording in a rubric is a contamination path.** Asking for "the required terminology" lets
  whichever arm shares the reference's vocabulary win.
- **Check the judge's reasons against the evidence, not only its scores.** The Faithfulness
  scores looked plausible, from 0.88 to 1.0. Only the reasons showed the judge had misread the
  dates in the context.
- **Say what not to penalize.** Removing a step isn't enough. A judge falls back on its own idea
  of a good answer unless the rubric rules it out.
- **Test a more lenient rubric on a wrong answer.** An answer that improves under the new rubric
  only shows that it's more lenient. The "escalating fault" answer staying at 0.2 is what showed
  the rubric still discriminates.
- **A "Must not claim" item has to forbid only what's false.** "Something new broke" overlaps
  with the true statement that the situation got worse, and the judge's spread of 0.5 to 0.8
  came from that overlap.
- **A check that passes is only as strong as the reason it passed.** The wrong-arm run stopped on
  the first try, but only because `RULES.md` happened to differ. Reading which files it reported,
  not just that it stopped, is what exposed that it couldn't see files the manifest doesn't list.
- **Test a refusal with the change it should refuse, through every path.** `compare` had unit
  tests for same-arm and different-arm pairs. Nobody had asked what an unlabeled run counts as.
- **Rebuilding the image doesn't rebuild the arm.** The dataset lives in the arm, so the q018
  change reached the agent only after `build-arm.sh` ran again. Check the hash in `arm.json`
  after every rebuild.

## Still open

- ~~Commit the new rubric, then rebuild `nao:study` and the demo so runs use it.~~ Done; the B
  smoke run used `0015f7a322a7`.
- ~~Tighten q018's "Must not claim" item~~ and the "Oct 1 to Oct 14" requirement: done in
  `8938426c`. Still to do: rejudge the borderline `20261106_020913` answer against the new
  reference, which has to be swapped into a copy of its results file, to see whether its spread
  narrows.
- Review the A/B pairing run's results files. It was reported to pass but hasn't been checked
  here: the only expected differences are the arm's files.
- Two misleading messages: `compare` says "except the arm" for runs of the same arm, and a run
  stopped by `--max-cost` ends with "✓ All N eval(s) passed".
- Whether omissions leaking within the top bands needs a fix, for example a 9–10 band that says
  omissions don't lower the score.
- Validate Faithfulness against human labels, or record it as exploratory only. Its errors on
  answer 2 could become open decision 5 in the experiment plan.
- Rewrite the other 11 references in the "Required / Must not claim" format, so the new
  Correctness step applies to them.
- Whether Completeness needs score bands too.
- ~~Step 5: cost ledger and `--max-cost`.~~ Done; the smoke run recorded both costs.
- ~~The compare step and `--confirmatory`.~~ Implemented; compare is checked live in check 5.
- Arm D's degradations.
- Rechecking q015–q017 (the "18% drop" premise is 11.9 pp in the data).
- `persist_docs`.
- Optionally, record failed tool calls with their error message.
