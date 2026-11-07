# Retrospective: labeling, repeating, and rejudging runs

**Date:** 2026-11-06
**Scope:** instrumentation step 2: arm labels, repetition, blocks, a shuffled order, and
rejudging saved answers.
**Status:** built, unit-tested (73 eval tests pass, lint clean) and committed (`a1206818`).
One live check passed: q018, arm B, two repetitions (`evals_results_20261106_222427.json`).
Step 5 (cost), the compare step and `--confirmatory` are not started. No baseline has been run.

This follows the [2026-11-05 retrospective](retrospective_2026-11-05.md). The design lives in
the [instrumentation plan](instrumentation_plan.md#2-arm-label-repetition-and-block) and the
[runbook](running_evals.md#runs-that-count).

---

## Context

By the end of 2026-11-05 each result recorded what the agent saw and which versions it ran
against. It still couldn't say which arm produced it, and each case could be asked only once.
That left two gaps:

- **No arm or block label.** Results from arm A and arm B would look the same in the file, and
  a label can't be added to a finished run afterwards.
- **No repetition.** The q018 runs varied a lot from run to run (Correctness 0.3 to 0.7), so a
  single answer per case can't tell an effect of the tree from noise. There was also no way to
  tell whether that spread came from the agent or the judge.

Step 2 was picked over cost tracking (step 5) and the compare step because, of the remaining
gaps, it is the only one with no retroactive fix.

---

## Decisions

### 1. Every repetition is its own record

**Considered:** one record per case with a list of scores, or an averaged score.
**Chosen:** `--repeats N` makes N agent calls, and each one is judged and saved as its own
record, with `repetition` (1..N) and a fresh `answer_id`.
**Why:** the analysis needs the per-answer scores to estimate run-to-run variance and to pair
arms case by case. An average in the file would throw that away, and a list would make the
answer, its tool calls and its scores harder to keep together.

### 2. Labels on every record, not only on the file

**Chosen:** each record carries `run_id`, `experiment_id`, `arm`, `block`, `repetition`,
`position` and `started_at`. The file's `run` section repeats the labels and adds the seed,
the full trial order and the arm manifest.
**Why:** analysis will pool records from many results files. A record that only makes sense
inside its file would lose its arm the moment it's concatenated with others.

### 3. The arm comes from a manifest, not a flag

**Considered:** an `--arm B` flag, or the `arms.yaml` sketched in the plan, mapping each arm to
its expected context hash.
**Chosen:** no `--arm` flag. `build-arm.sh` now writes `arm.json` next to the arm, holding the
arm, the study commit and each file's hash. `nao evals --arm-manifest` takes the arm from it,
and before the first agent call it compares every file in the manifest with the context the
backend serves. Any difference stops the run.
**Why:**

- A typed label can be wrong. The failure that matters is a stale image: the arm folder was
  rebuilt but the demo image wasn't, so the backend still serves the old arm. That happened on
  2026-11-05, when the arm's copy of `RULES.md` hid an edit. A hash check catches it; a flag
  doesn't.
- `arms.yaml` would need each arm's context hash copied in by hand after every rebuild, and
  forgetting to do that is the same failure in another place. The manifest is written by the
  same script that builds the arm, so it can't go stale relative to it.
- The dataset is compared with the local project, because the backend's context fingerprint
  skips `tests/`.

**Consequence:** `arm.sha256` is replaced by `arm.json`. The kwwhat `.gitignore` and the
runbook were updated to match. The manifest's hashes match the old `arm.sha256`, so the arm's
contents didn't change.

### 4. Experiment runs must be fully labeled

**Chosen:** `--experiment` without `--arm-manifest` and `--block` stops before any call.
Runs without `--experiment` stay as they were: unlabeled, in dataset order.
**Why:** a run that counts and is missing a label costs money and can't be used. Stopping
early is free. Smoke runs and single-case checks keep the simple behavior, since they're never
evidence.

### 5. A seeded shuffle within each block

**Considered:** dataset order, or a shuffle without a recorded seed.
**Chosen:** experiment runs shuffle cases and repetitions together. The seed is drawn at
random unless `--seed` is passed, and it's recorded either way.
**Why:** the provider's latency, load and model serving can drift during a block. In dataset
order the last cases would get all of that drift, and it would look like a difference between
cases. Shuffling spreads it randomly, and keeps repetitions of one case apart. The recorded
seed makes the order reproducible, and `position` and `started_at` let drift be checked
afterwards. See the [runbook](running_evals.md#why-the-order-is-shuffled).

### 6. Alternating arms is a procedure, not code

**Chosen:** blocks are run as A, B, B, A, each block one `nao evals` run against one built arm.
**Why:** one backend serves one project folder at a time, so the CLI can't interleave arms
inside a run. The shuffle handles drift within a block; alternation handles drift between
blocks.

### 7. Rejudging saved answers

**Chosen:** `nao evals rejudge <results.json> --judge-repeats N` scores the saved answers again
without calling the agent. Each judgment records the answer's `answer_id`, `arm`, `block` and
`repetition`, plus its own `judge_repetition`.
**Why:** a score can change because the agent wrote a different answer or because the judge
scored the same answer differently. `--repeats` varies the answer; `rejudge` holds it fixed.
Spread within one answer's judgments is judge variance, and spread between answers to one case
is agent variance. If the judge's spread were as large as the agent's, more agent repetitions
wouldn't help rank the arms. See the
[runbook](running_evals.md#telling-judge-variance-from-agent-variance).

Choices inside the command:

- **A new file, not an edit.** It writes `rejudge_results_<timestamp>.json` and identifies the
  source by path and hash. A results file stays a record of what happened in that run.
- **The original run's settings by default.** It uses the original metrics, thresholds and
  judge, so a rejudge measures the judge, not a change of setup. `--metrics` and `-j` override
  them, and a rubric that changed since the run is warned about and recorded.
- **Only answers the agent produced are judged.** Timeouts, backend errors and context errors
  are listed under `skipped`. Answers that got a metric error are judged again, since
  recovering them is a use of the command.
- **Fresh metric objects for every judgment,** so no state carries over between repetitions.
- **Older files work.** Results from before `answer_id` existed get an ID from the file hash
  and the record's position, so yesterday's q018 runs can be rejudged.

**A side benefit:** rubric changes in Phase 4 can be tested on saved answers, so judge work
doesn't spend agent calls from the $200 budget.

---

## What was added

| Part                      | What it does                                                                                                                   |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| `evals/schedule.py`       | Run labels, the seed, and the trial order: one trial per case and repetition, shuffled if seeded                               |
| `evals/arm.py`            | Loads `arm.json` and lists every file that is missing or differs from what the backend serves                                  |
| `evals/runner.py`         | The new flags, labels on each record, the arm check before the first call, and the `run` section                               |
| `evals/rejudge.py`        | The `nao evals rejudge` command                                                                                                |
| `study/build-arm.sh`      | Writes `arm.json` (arm, study commit, file hashes) in place of `arm.sha256`                                                    |
| Tests                     | `test_evals_arm.py`, `test_evals_schedule.py`, `test_evals_rejudge.py`, and new runner tests                                   |
| `running_evals.md`        | The labeled command, a two-repetition example in §5, the rebuild note for `RULES.md`, rejudging, and why the order is shuffled |
| `instrumentation_plan.md` | Step 2 marked done, with how it differs from the sketch                                                                        |
| kwwhat `.gitignore`       | `demo/chat-bi/arm.json` in place of `demo/chat-bi/arm.sha256`                                                                  |

---

## Where the eval library made a difference

- **No retroactive fix.** The same rule that put instrumentation first on 2026-11-05 put
  step 2 ahead of cost tracking and the compare step today. It also motivated stopping
  experiment runs that are missing labels.
- **Check the label instead of trusting it** (`braintrust-design-eval-instrumentation`:
  record the resolved configuration, not the intended one). This is why the arm comes from a
  hash-checked manifest rather than a flag.
- **Randomization and blocking** (`braintrust-design-eval-experiment`). These are the shuffle,
  the recorded seed, and the A, B, B, A blocks.
- **Run-to-run variance is part of the result** (`braintrust-probe-capability-and-variability`).
  This is why repetitions are separate records and why judge variance is measured apart from
  agent variance.

---

## The first live run

`evals_results_20261106_222427.json`: q018, arm B, `--repeats 2 --arm-manifest`, no
`--experiment`.

### Plumbing: correct

- **Labels:** `arm: B` came from the manifest, and the check passed. The manifest's
  `study_commit` (`a1206818`) is clean.
- **Repetitions:** there are two records, `repetition` 1 and 2 at positions 0 and 1, with
  distinct `answer_id`s and one `run_id`.
- **Order:** `seed` is null and the order is the dataset order, as designed for a run without
  `--experiment`.
- **Environment:** the nao commit is `5f46a96`, with no `-dirty` suffix, and the environment
  didn't change during the run. `story` was excluded and the memory count was 0. Both
  repetitions had the same system prompt hash.
- **One flag: kwwhat showed `dirty: True`.** The cause was the uncommitted `.gitignore` edit
  (`arm.sha256` → `arm.json`) on `exp/metric_tree`.

### What the agent did

- **Both repetitions read the root cause skill and the metrics tree.** Repetition 2 also read
  four `columns.md` files, so the table metadata reaches the agent.
- **Both called `load_skill("root-cause-analysis")` first.** That call fails, because
  `load_skill` serves only built-in skills. The agent then opened the file with `read`, as the
  skills rule says. It costs one turn and does no harm.
- **Instrumentation gap:** the failed call is recorded with no `output` and no error.
  `extractToolCalls` collects only `toolResults`, and the AI SDK reports failed tool calls
  separately, so a failed call looks the same as an empty result. Tool errors aren't a priority,
  but recording the message in `test-agent.service.ts` would be a small fix.

### Scores

| Repetition | Correctness | Completeness | Faithfulness | ContextualRelevancy |
| ---------- | ----------- | ------------ | ------------ | ------------------- |
| 1          | **1.0**     | 1.0          | 1.0          | 0.65                |
| 2          | **0.7**     | 0.9          | 1.0          | 0.60                |

1. **Repetition 1 is the best q018 answer so far**, better than the 02:20 run on 2026-11-05.
   It names the mix shift explicitly, gives both chargers' rates on both days, and says Oct 4
   was the exception, not Oct 5.
2. **Same arm, same case, a 0.3 difference.** This is the run-to-run variance repetitions are
   for. Both answers are right about the cause. Repetition 2 doesn't mention CH-001 at all, and
   it describes the drop as "random daily variation in how many drivers choose the broken port"
   instead of a mix shift between two chargers with stable rates.
3. **Correctness is penalizing an omission.** The judge's Correctness reason for repetition 2
   is that it "omits" CH-001's 100% and the explicit mix-shift framing. Repetition 2 states
   nothing false, and leaving facts out is what Completeness measures. Yet Completeness gave
   0.9 while Correctness gave 0.7, the reverse of what you'd expect. The two metrics' reasons
   are nearly the same text. So the rubrics don't separate "wrong" from "missing", and
   Correctness is the primary metric. This is a Phase 4 rubric problem, and it would have
   stayed hidden without two answers to the same case.
4. **The reference has a weak spot.** Both judgments mention "Oct 1 to Oct 14". The answers
   checked only Oct 1–5, and the judge called that a "minor discrepancy". An answer about
   Oct 4–5 doesn't need to cover Oct 14, so the criterion is awkward. It fits the planned
   tightening of q018's reference.
5. **Faithfulness is 1.0 on both**, even though repetition 2 says 100% uptime is "ruling out a
   hardware outage" and then calls the fault "a hardware/EVSE fault". As on 2026-11-05,
   Faithfulness can't see reasoning errors.

### Cost and time

- **Agent cost:** about $0.25 per answer ($0.28 and $0.22), recorded in the file.
- **Judge cost:** not recorded anywhere.
- **Time:** each answer took about 85 seconds from the agent, but the trials started 5 minutes
  apart. Judging takes about 3.5 minutes per answer, longer than the agent.

The judge cost is the main unknown for the $200 budget, which is what step 5 is for.

---

## Caveats

- **The judge is pinned at temperature 0** (2026-11-05 retrospective, §8). Judge repetitions
  therefore measure only the provider's leftover nondeterminism: batching and floating-point
  order flip near-tied tokens, and one flip can change a verdict. A spread near zero is the
  expected result. GEval scores move in steps of 0.1, because the Claude judge returns no token
  probabilities. The multi-step RAG metrics will likely vary more.
- **Reproducible is not right.** Repetition can't reveal a bias the judge has every time, such
  as the Correctness rubric penalizing omissions in the first live run. Rejudging that answer
  would very likely give 0.7 each time. Nor can it reveal sensitivity to the rubric's wording,
  the effect of judging with the agent's own model, or how confident the judge is. The
  whitepaper should report judge repetitions as reproducibility, a lower bound on judge noise,
  and report agreement with human labels separately as accuracy. Rejudging at temperature 1
  was rejected because it would measure a different instrument from the one that produced the
  scores. See the
  [runbook](running_evals.md#what-judge-repetitions-can-and-cant-show).

    How to read a rejudge result:

    | What you see                               | What it means                                                                                                         |
    | ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
    | Same score every time                      | Expected. The judge is reproducible on this answer, which says nothing yet about whether it's right.                  |
    | Occasional 0.1 steps                       | The answer sits near a rubric boundary. Fine, as long as the steps are small next to the differences between answers. |
    | Spread as large as the gap between answers | The judge can't rank these answers. More agent repetitions won't help; the rubric needs work first.                   |

- **The study commit was `-dirty` in the manifest test,** because `build-arm.sh` itself was
  uncommitted. Arms built for runs that count should come from a clean commit.
- **One live run is a check, not evidence.** The scores above are two answers to one case, read
  for what they reveal about the pipeline and the rubric, not as a result for arm B.

## Lessons

- **Yesterday's failure shaped today's design.** The stale `RULES.md` snapshot is why the arm
  check compares hashes, not names.
- **Derive what can be derived.** The manifest is written by the script that builds the arm,
  so there's nothing to copy by hand and nothing to forget.
- **Keep the raw unit.** One record per answer, and one judgment per judge repetition, keeps
  every later analysis open; averaging can always happen later, but it can't be undone.

## Still open

- Commit the kwwhat `.gitignore` change on `exp/metric_tree`, so kwwhat stops showing as dirty.
- Rejudge `evals_results_20261106_222427.json` with `--judge-repeats 3`, to tell whether the
  1.0 versus 0.7 gap comes from the two answers or from the judge.
- Record the Correctness/Completeness overlap as a Phase 4 finding in the experiment plan.
- Optionally, record failed tool calls with their error message.
- Step 5: cost ledger and `--max-cost`.
- The compare step and `--confirmatory`.
- Arm D's degradations.
- Rechecking q015–q017 (the "18% drop" premise is 11.9 pp in the data).
- Whether to tighten q018's "must not claim" line.
- `persist_docs`.
- The minimum meaningful improvement in Correctness, after the pilot measures noise.
