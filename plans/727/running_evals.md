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
  served project isn't that arm (see [Runs that count](#runs-that-count)). Without it the
  run's `arm` is empty.
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

## 6. Find the results

`chat-bi/tests/outputs/` is mounted from the host, so results appear in
`~/github/kwwhat/demo/chat-bi/tests/outputs/`:

| Path                               | Contents                                                             |
| ---------------------------------- | -------------------------------------------------------------------- |
| `evals_results_<timestamp>.json`   | Every case: answer, scores, tool calls, run context, provenance      |
| `rejudge_results_<timestamp>.json` | New scores for the answers in one results file, per judge repetition |
| `prompts/<sha256>.txt`             | Each distinct system prompt, referred to by hash                     |
| `tool_manifests/<sha256>.json`     | Each distinct tool set, referred to by hash                          |

## Before trusting a result

Check these in the results file:

- `run.arm` and `run.block` are the arm and block you meant to run.

- `provenance.environment_changed` is empty.
- `provenance.environment_start.nao.commit` is the commit you built, without `-dirty` for runs
  that count.
- `run_context.tool_names` doesn't include `story`.
- `run_context.memory_count` is 0.

## Switching arms

Repeat steps 3 and 4 with the other arm. The nao image and the data volume stay as they are.
