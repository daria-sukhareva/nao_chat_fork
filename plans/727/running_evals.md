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

Add `demo/chat-bi/arm/` and `demo/chat-bi/arm.sha256` to the kwwhat `.gitignore`, so a built
arm doesn't mark the repo as dirty.

## 3. Build the arm

```bash
rm -rf ~/github/kwwhat/demo/chat-bi/arm ~/github/kwwhat/demo/chat-bi/arm.sha256
~/github/nao_chat_fork/plans/727/study/build-arm.sh B ~/github/kwwhat/demo/chat-bi ~/github/kwwhat/demo/chat-bi/arm
```

- The first argument is the arm: `A`, `B`, or `N`. Arm D is not defined yet.
- `build-arm.sh` refuses to overwrite, so delete the previous arm first.
- The file hashes go to `chat-bi/arm.sha256`, outside the project, where the agent can't
  read them.

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
docker exec -it "$(docker ps -qf name=chat-bi-run)" sh -c 'cd /app/kwwhat && nao evals -s q016 -u <your nao login>'
```

- Drop `-s q016` to run every case.
- `-u` is the account you sign in with at http://localhost:5005. The password is prompted
  for, or read from `NAO_PASSWORD`.

## 6. Find the results

`chat-bi/tests/outputs/` is mounted from the host, so results appear in
`~/github/kwwhat/demo/chat-bi/tests/outputs/`:

| Path                             | Contents                                                        |
| -------------------------------- | --------------------------------------------------------------- |
| `evals_results_<timestamp>.json` | Every case: answer, scores, tool calls, run context, provenance |
| `prompts/<sha256>.txt`           | Each distinct system prompt, referred to by hash                |
| `tool_manifests/<sha256>.json`   | Each distinct tool set, referred to by hash                     |

## Before trusting a result

Check these in the results file:

- `provenance.environment_changed` is empty.
- `provenance.environment_start.nao.commit` is the commit you built, without `-dirty` for runs
  that count.
- `run_context.tool_names` doesn't include `story`.
- `run_context.memory_count` is 0.

## Switching arms

Repeat steps 3 and 4 with the other arm. The nao image and the data volume stay as they are.
