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
plans/727/study/build-arm.sh B ~/github/kwwhat/demo/chat-bi ~/github/kwwhat/demo/chat-bi/arm
```

The output holds the demo's `RULES.md` with the arm's rule appended and every overlay file.
`<output>.json`, next to the output folder, is the arm's manifest: the arm, the study commit,
and a hash of each file. It stays outside the project so the agent can't read it.
`nao evals --arm-manifest` checks the served project against it and labels the run with its arm.

For the full sequence, from building the nao image to reading results, see
[Running the evals](../running_evals.md).
