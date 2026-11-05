# Study files

The files each arm adds to the `kwwhat/demo/chat-bi` project. See the
[experiment plan](../experiment_plan.md) for the design.

| Folder    | Used by    | Contents                                                                        |
| --------- | ---------- | ------------------------------------------------------------------------------- |
| `common/` | Every arm  | The root cause skill and the eval dataset                                       |
| `arm-b/`  | Arm B only | The metrics tree, the `count-active-drivers` skill, and the rule for `RULES.md` |

Arm N uses the same files as arm A. Arm D's degradations are not defined yet.

## Building an arm

```bash
plans/727/study/build-arm.sh B ~/github/kwwhat/demo/chat-bi build/arm-b
```

The output holds the demo's `RULES.md` with the arm's rule appended, every overlay file,
and `MANIFEST.sha256`, a hash of each file.

To build an image for the arm, copy the output into the demo's build context as `arm/`
and add this line to `chat-bi/Dockerfile`, after the existing `COPY` lines:

```dockerfile
COPY arm/ /app/kwwhat/
```

Build the nao base image from this branch with its commit, so every result records it:

```bash
docker build --build-arg APP_COMMIT="$(git rev-parse HEAD)$(git diff --quiet HEAD || echo -dirty)" -t nao:study .
```

Then point the demo's `FROM` line at `nao:study`. Tag each arm's image separately and record its digest. Only `RULES.md` overlaps a file
the demo already copies; the overlay version replaces it.
