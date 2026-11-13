# Running the evals

How to run `nao evals` for one arm of the [experiment](experiment_plan.md) against the kwwhat
demo. Paths assume both repos are checked out under `~/github`.

Every result records the `nao` commit, the context, and the data it ran against (see the
[instrumentation plan](instrumentation_plan.md)), so a step done out of order shows up in the
result instead of going unnoticed.

---

## 1. Build the nao image from this branch

From the fork's root:

```bash
cd ~/github/nao_chat_fork
docker build --build-arg APP_COMMIT="$(git rev-parse HEAD)$(git diff --quiet HEAD || echo -dirty)" -t nao:study .
```

`APP_COMMIT` ends in `-dirty` when the build includes uncommitted changes. That is fine for
checks, but runs that count need a clean commit.

If the command fails with `'docker buildx build' requires 1 argument`, the trailing `.` was
lost while pasting. Run it in two steps instead:

```bash
COMMIT="$(git rev-parse HEAD)$(git diff --quiet HEAD || echo -dirty)"
docker build --build-arg "APP_COMMIT=$COMMIT" -t nao:study ~/github/nao_chat_fork
```

Rebuild this image after every change to the backend or the CLI.

## 2. Point the demo at the image

Two lines in `~/github/kwwhat/demo/chat-bi/Dockerfile`, done once:

```dockerfile
FROM nao:study

# ...existing COPY lines...
COPY arm/ /app/kwwhat/
```

- `FROM nao:study` replaces `FROM getnao/nao:latest`.
- `COPY arm/ /app/kwwhat/` goes after the existing `COPY` lines, so the arm's `RULES.md`
  replaces the demo's.

Add `demo/chat-bi/arm/` and `demo/chat-bi/arm.json` to the kwwhat `.gitignore`, so a built
arm doesn't mark the repo as dirty.

## 3. Build the arm

```bash
rm -rf ~/github/kwwhat/demo/chat-bi/arm ~/github/kwwhat/demo/chat-bi/arm.json
~/github/nao_chat_fork/plans/727/study/build-arm.sh B ~/github/kwwhat/demo/chat-bi ~/github/kwwhat/demo/chat-bi/arm
```

- The first argument is the arm: `A`, `B`, or `N`. Arm D is not defined yet.
- `build-arm.sh` refuses to overwrite, so delete the previous arm first.
- The manifest goes to `chat-bi/arm.json`, outside the project, where the agent can't read it.
  It records the arm, the study commit, and a hash of each file. An `arm.sha256` left by an
  earlier version of the script is no longer used and can be deleted.
- The arm copies the demo's `RULES.md` when it's built. After editing that file, rebuild the
  arm and the demo image, or the change won't reach the agent.

The files for each arm are described in [`study/README.md`](study/README.md).

## 4. Build and start the demo

From `~/github/kwwhat/demo`:

```bash
docker compose build chat-bi
docker compose run --rm --service-ports chat-bi
```

`--service-ports` is required: `docker compose run` doesn't publish ports without it. Wait for
"kwwhat demo is ready!", then http://localhost:5005 loads.

Wipe the data volume first when the dbt models or the schema change; otherwise tables
from the old build stay in `analytics.duckdb`:

```bash
docker compose down -v
docker volume ls | grep duckdb   # should print nothing
```

## 5. Run the evals

In a second terminal, inside the running container, where the arm's dataset and the
backend are:

```bash
docker exec -it "$(docker ps -qf name=chat-bi-run)" sh -c 'cd /app/kwwhat && nao evals \
  -s q018 --repeats 2 --arm-manifest /kwwhat/demo/chat-bi/arm.json -u <your nao login>'
```

- Drop `-s q018` to run every case.
- `--repeats 2` asks each case twice. Every answer is judged and saved as its own record.
- `--arm-manifest` labels the run with the arm and stops it before the first agent call if the
  served project isn't that arm (see [Runs that count](#runs-that-count)): an arm file is
  missing or different, or a file is served that the arm doesn't list. Files under
  `databases/` and `repos/`, and `nao_config.yaml`, are the same for every arm and aren't
  checked. Without the flag the run's `arm` is empty.
- `-u` is the account you sign in with at http://localhost:5005. The password is prompted
  for, or read from `NAO_PASSWORD`.

### Runs that count

Label the run with the experiment, the arm's manifest, and the block:

```bash
docker exec -it "$(docker ps -qf name=chat-bi-run)" sh -c 'cd /app/kwwhat && nao evals \
  --experiment metrics-tree-001 --arm-manifest /kwwhat/demo/chat-bi/arm.json --block 1 --repeats 3 \
  -u <your nao login>'
```

- The manifest is visible in the container because the kwwhat repo is mounted at `/kwwhat`.
- The arm comes from the manifest, not from a flag. Before the first agent call, the run stops
  if any file the backend serves differs from the manifest, so a stale image can't be labeled
  as the arm you meant to run.
- `--experiment` requires `--arm-manifest` and `--block`. It also shuffles the order of cases
  and repetitions. The seed is drawn at random unless you pass `--seed`, and it is recorded
  either way.
- Number blocks across the experiment and alternate the arms, A, B, B, A, so that slow
  provider drift doesn't line up with one arm. Each block is one `nao evals` run against one
  built arm.

#### Why the order is shuffled

The provider's latency, load and model serving can drift during a block. In dataset order,
q001 always runs first and q018 always runs last, so drift would look like a difference
between cases, and the last cases would get all of it. Shuffling spreads drift randomly over
cases instead. It also keeps repetitions of one case apart, so they're less likely to share one
bad moment at the provider.

For 2 cases × 2 repetitions:

| `position` | Dataset order (no seed) | Shuffled (with a seed) |
| ---------- | ----------------------- | ---------------------- |
| 0          | q001, repetition 1      | q002, repetition 1     |
| 1          | q001, repetition 2      | q001, repetition 2     |
| 2          | q002, repetition 1      | q001, repetition 1     |
| 3          | q002, repetition 2      | q002, repetition 2     |

The same seed always gives the same order, and the file's `run.order` lists it. Each record
keeps its `position` and `started_at`, so drift can be checked afterwards, for example by
plotting score against position.

Shuffling works within a block. Drift between blocks is what alternating the arms is for.

### Confirmatory runs

Add `--confirmatory` to a labeled run once the study is preregistered:

```bash
docker exec -it "$(docker ps -qf name=chat-bi-run)" sh -c 'cd /app/kwwhat && nao evals \
  --experiment metrics-tree-001 --arm-manifest /kwwhat/demo/chat-bi/arm.json --block 1 --repeats 3 \
  --max-cost 20 --confirmatory -u <your nao login>'
```

It refuses to start, before any agent call, if:

- `--experiment`, `--arm-manifest` or `--block` is missing;
- `-s` is given, because a confirmatory run uses the whole dataset;
- the arm was built from an uncommitted study (`study_commit` ends in `-dirty`);
- the nao build, or a linked repo such as kwwhat, isn't a clean commit;
- the backend can't describe its environment.

After the run, `run.confirmatory` records whether it's valid. It's invalid, and the command
exits with an error, if anything in `provenance.environment_changed` changed during the run, or
if the run stopped early because of `--max-cost` or Ctrl-C. The dataset now counts as part of
the environment: it's fingerprinted when the cases are loaded and again at the end, so an edit
mid-run shows up as `dataset`.

### Checking runs before pairing them

Before pairing or pooling runs, for example the blocks of A and B, check that they held
everything fixed except the arm:

```bash
cd ~/github/kwwhat/demo/chat-bi/tests/outputs
nao evals compare evals_results_<block1>.json evals_results_<block2>.json ... --confirmatory
```

It exits with an error, listing each problem, if:

- **Something that must be fixed differs between any two runs:** the experiment, the nao
  commit, the dataset, the data checksums, the linked repos' commits, package versions, the
  metric configuration and rubric versions, the agent model and its settings, the tool
  manifest, or the judge model and its settings.
- **Two runs of the same arm differ** in any project file or in the system prompt.
- **Two runs of different arms differ** in a file that isn't one of either arm's manifest
  files. An edit to the demo's `RULES.md` between builds also changes the kwwhat commit, so
  it's caught too.
- **A run changed during itself,** stopped early, has a value that varies between its records,
  or shares a block number with another run.
- With `--confirmatory`, a run isn't a valid confirmatory run.

One difference is tolerated but always reported: a table's `preview.md` may differ when the
data checksums are identical. `nao sync` writes previews with `LIMIT 10` and no `ORDER BY`, and
the demo syncs on every container start, so different containers can show the agent different
sample rows of the same data. The whitepaper reports this as an uncontrolled difference (see the
experiment plan's threats).

### Rescoring saved answers

`nao evals rejudge` scores the answers in a results file again without calling the agent:

```bash
docker exec -it "$(docker ps -qf name=chat-bi-run)" sh -c 'cd /app/kwwhat && nao evals rejudge \
  tests/outputs/evals_results_<timestamp>.json --judge-repeats 3'
```

- It needs no nao login, only the judge's API key, which the container already has.
- Each judgment records `answer_id` and `judge_repetition`.
- It uses the original run's metrics, thresholds and judge. `--metrics` and `-j` override them.
  If a rubric changed since the run, it warns and records the new rubric version.
- Answers the agent never produced (timeouts, backend and context errors) are listed under
  `skipped` and not judged.
- It writes `rejudge_results_<timestamp>.json` next to the source file and leaves the source
  file unchanged.

#### Telling judge variance from agent variance

A score can change between runs for two reasons: the agent wrote a different answer, or the
judge scored the same answer differently. The two commands separate them.

- `nao evals --repeats` asks the agent the same case several times. Each answer gets its own
  `answer_id`.
- `nao evals rejudge --judge-repeats` scores each of those answers several times. The text being
  scored never changes, so any spread comes from the judge alone.

For example, after `nao evals -s q018 --repeats 2` and `nao evals rejudge <file> --judge-repeats 3`:

| Case | Repetition | `answer_id` | Correctness, judge repetitions 1, 2, 3 |
| ---- | ---------- | ----------- | -------------------------------------- |
| q018 | 1          | `a1…`       | 0.7, 0.7, 0.6                          |
| q018 | 2          | `b2…`       | 0.3, 0.3, 0.3                          |

- **Judge variance** is the spread within a row: the same answer, scored three times
  (0.6 to 0.7 for `a1…`).
- **Agent variance** is the spread between rows: different answers to the same case
  (about 0.67 versus 0.3).

Here the judge barely moves, and the agent's two answers differ by about 0.4. So the
difference comes from the agent. If the spread within rows were as large as the spread between
rows, the judge would be too noisy to rank the arms, and more agent repetitions wouldn't help.

The scores above are made up to show the reading, not measured.

#### What judge repetitions can and can't show

The judge runs at temperature 0, so it always takes the most likely next token. If serving
were exact, rejudging would give the same score every time. It isn't quite exact: requests are
batched on shared hardware, floating-point sums depend on order, and when two tokens are nearly
tied a tiny difference decides which wins. One flipped token early in the judge's reasoning can
change its verdict. Judge repetitions measure that leftover nondeterminism, which is how close a
verdict sits to a tie.

Two things shape what you'll see:

- **GEval scores move in steps of 0.1.** Our Claude judge returns no token probabilities, so
  Correctness and Completeness are an integer from 0 to 10, divided by 10. Judge variance shows
  up as occasional jumps of 0.1, not small continuous noise.
- **The RAG metrics vary more.** Faithfulness and ContextualRelevancy first extract claims or
  statements, then judge each one. One more or one fewer statement changes the ratio.

| What you see                               | What it means                                                                                                         |
| ------------------------------------------ | --------------------------------------------------------------------------------------------------------------------- |
| Same score every time                      | Expected. The judge is reproducible on this answer, which says nothing yet about whether it's right.                  |
| Occasional 0.1 steps                       | The answer sits near a rubric boundary. Fine, as long as the steps are small next to the differences between answers. |
| Spread as large as the gap between answers | The judge can't rank these answers. More agent repetitions won't help; the rubric needs work first.                   |

A spread near zero shows the judge is reproducible, not that it is right. Repetition can't
reveal:

- **Consistent bias.** A judge that marks down omissions under Correctness does so every time:
  zero spread, wrong construct. Only comparison with human labels finds it (Phase 4).
- **Sensitivity to the rubric's wording.** That needs the rubric paraphrased and the answers
  rescored.
- **The choice of judge model.** The judge is the same model as the agent, a bias flagged for
  the whitepaper.
- **How confident the judge is.** At temperature 0 a 51% verdict and a 99% verdict look the
  same.

Rejudging at temperature 1 would show that last one, but it would measure a different
instrument from the one that produced the scores. `rejudge` keeps the original judge settings
for that reason.

In the whitepaper, report this as judge reproducibility, a lower bound on judge noise, and
report the judge's agreement with human labels separately as its accuracy.

### Cost

Every run records what it spent, and the study's $200 budget covers agent and judge calls
together.

- **Per record:** the agent's cost (`cost`, from nao's backend), and the judge's tokens and cost
  for each metric (`metrics[].judge_cost`) and in total (`judge_cost`).
- **Per run:** `run.cost` has the agent, judge and total cost in US dollars, and how many agent
  calls or judge metrics reported no cost.
- **Across runs:** each `nao evals` and `nao evals rejudge` appends one line to
  `tests/outputs/cost_ledger.jsonl`, including runs where cases errored.

Cap a run with `--max-cost`, in US dollars, on either command:

```bash
docker exec -it "$(docker ps -qf name=chat-bi-run)" sh -c 'cd /app/kwwhat && nao evals \
  --experiment metrics-tree-001 --arm-manifest /kwwhat/demo/chat-bi/arm.json --block 1 --repeats 3 \
  --max-cost 20 -u <your nao login>'
```

- The check runs before each trial, so the trial in flight can overshoot the limit by its own
  cost (about $0.25 for the agent, plus the judge).
- Finished trials are saved, and the file's `run.stopped` says why the run ended early. The
  command then exits with an error, because the run is incomplete.
- Ctrl-C also saves what's finished, with `run.stopped.reason` set to `interrupted`.
- A judge model with no known price stops a capped run, because the limit can't be enforced.
  Only `claude-sonnet-4-6` is priced, from nao's own price table.
- A trial that times out returns no agent cost. It's counted in `agent_cost_unknown`, but it
  doesn't stop the run.

See what the experiment has spent so far:

```bash
docker exec -it "$(docker ps -qf name=chat-bi-run)" sh -c 'cd /app/kwwhat && nao evals cost \
  --experiment metrics-tree-001 --budget 200'
```

Without `--experiment`, it lists every experiment, with unlabeled runs grouped as
"(no experiment)".

## 6. Find the results

`chat-bi/tests/outputs/` is mounted from the host, so results appear in
`~/github/kwwhat/demo/chat-bi/tests/outputs/`:

| Path                               | Contents                                                             |
| ---------------------------------- | -------------------------------------------------------------------- |
| `evals_results_<timestamp>.json`   | Every case: answer, scores, tool calls, run context, provenance      |
| `rejudge_results_<timestamp>.json` | New scores for the answers in one results file, per judge repetition |
| `prompts/<sha256>.txt`             | Each distinct system prompt, referred to by hash                     |
| `tool_manifests/<sha256>.json`     | Each distinct tool set, referred to by hash                          |
| `cost_ledger.jsonl`                | One line per run, with its agent, judge and total cost               |

## Before trusting a result

Check these in the results file:

- `run.arm` and `run.block` are the arm and block you meant to run.
- `run.stopped` is null, so the run wasn't cut short by `--max-cost` or Ctrl-C.
- For runs that count, `run.confirmatory.valid` is true.
- `provenance.environment_changed` is empty.
- `provenance.environment_start.nao.commit` is the commit you built, without `-dirty` for runs
  that count.
- `run_context.tool_names` doesn't include `story`.
- `run_context.memory_count` is 0.

## Switching arms

Repeat steps 3 and 4 with the other arm. The nao image and the data volume stay as they are.
Then check the new run against the earlier ones with `nao evals compare`.
