# Retrospective: labeling, repeating, and rejudging runs

**Date:** 2026-11-06
**Scope:** instrumentation step 2: arm labels, repetition, blocks, a shuffled order, and
rejudging saved answers.
**Status:** built and unit-tested (73 eval tests pass, lint clean), but not yet run against the
live container. Not committed. Step 5 (cost), the compare step and `--confirmatory` are not
started. No baseline has been run.

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

## Caveats

- **The judge is pinned at temperature 0** (2026-11-05 retrospective, §8). Judge repetitions
  therefore measure only the provider's leftover nondeterminism, and a spread near zero is the
  expected result. It's still worth measuring, because the whitepaper needs to show the judge
  isn't where the variance comes from.
- **The study commit was `-dirty` in the manifest test,** because `build-arm.sh` itself was
  uncommitted. Arms built for runs that count should come from a clean commit.
- **Nothing here has run against the live container yet.** The unit tests use a fake backend.

## Lessons

- **Yesterday's failure shaped today's design.** The stale `RULES.md` snapshot is why the arm
  check compares hashes, not names.
- **Derive what can be derived.** The manifest is written by the script that builds the arm,
  so there's nothing to copy by hand and nothing to forget.
- **Keep the raw unit.** One record per answer, and one judgment per judge repetition, keeps
  every later analysis open; averaging can always happen later, but it can't be undone.

## Still open

- A live check: rebuild the arm and image, then run `-s q018 --repeats 2 --arm-manifest
/kwwhat/demo/chat-bi/arm.json`, then `rejudge` the result.
- Commit step 2 (fork) and the `.gitignore` change (kwwhat, `exp/metric_tree`).
- Step 5: cost ledger and `--max-cost`.
- The compare step and `--confirmatory`.
- Arm D's degradations.
- Rechecking q015–q017 (the "18% drop" premise is 11.9 pp in the data).
- Whether to tighten q018's "must not claim" line.
- `persist_docs`.
- The minimum meaningful improvement in Correctness, after the pilot measures noise.
