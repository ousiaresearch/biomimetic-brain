# VALIDATION — The Copper Observatory (Ousia Mind Kit)

Presence is not the same as working. This kit is easy to install and easy to leave inert, so the checks below are the point of the kit rather than an afterthought.

## The two commands

```bash
python3 scripts/self_test.py           # the kit installs, runs, and does not lie about it
python3 scripts/decision-gate_test.py  # the gate's rule set, one assertion per rule
```

`self_test.py` builds a throwaway agent directory from the shipped examples, runs the shipped generator against it, and asserts what the kit claims. `decision-gate_test.py` builds synthetic states and asserts the **exact reason code** for every rule in `docs/DECISION_GATE.md` — 136 checks over 27 codes. A rule with no assertion beside it is not implemented. Expected `self_test.py` output, on a healthy tree:

```
  PASS  seeded 37 subsystem files from examples (expect >= 25)
  PASS  generator ran and wrote brain-state.json (rc=0)
  PASS  health_summary reports a total (got 25)
  PASS  aggregate carries per-system blocks (got 25)
  PASS  every system block carries age_h + max_age_h (25/25)
  PASS  generated aggregate carries no identity residue
  PASS  generator wrote into $MIND_AGENT_DIR, not into the kit
  PASS  README carries a runnable bash install block
  PASS  the README's own install block yields 25/25 healthy (rc=0)
  PASS  SHA256SUMS verifies (54/54 entries)
  PASS  an unseeded agent reports every subsystem missing, none stale (healthy=0 stale=0 missing=25)

11/11 checks passed
```

Checks 7–9 exist because the kit shipped without them: an install block that nothing executed, a checksum manifest that nothing verified, and a health summary where an absent subsystem was indistinguishable from a quiet one. Checks 5 and 6 are the ones that matter to anyone adopting this from someone else's tree: the kit must run on a neutral agent, and it must not carry the original agent's readings or paths along with it.

## What each check is really testing

| Check | The failure it catches |
|---|---|
| Seeded 37 files | Examples that do not cover the topology, so half the subsystems stay `missing` forever |
| Generator ran | The kit is copy-pasted into a host where nothing actually executes it |
| `health_summary.total >= 25` | A generator that silently reads an empty brain and reports success |
| Per-system blocks | Subsystems that exist as files but never reach the aggregate |
| `age_h` + `max_age_h` on every block | A copy of this kit where staleness was dropped, so an old number reads as a current one |
| No identity residue | A kit shipped with its author's readings, names or machine paths still inside it |
| Wrote into `$MIND_AGENT_DIR` | A generator that hardcodes a path from the tree it came from |
| The README's install block runs | Install instructions that seed a tree the kit cannot read — the defect shipped in `6b4bed3`, where the documented loop dropped the `brain/` component and a stranger following the docs got **0/25 healthy** while this test stayed green |
| `SHA256SUMS` verifies | A published checksum manifest that has drifted from the tree it describes, or that lists itself — an entry no file can ever satisfy |
| Unseeded → all `missing` | 18 of the 25 status sites had no existence test, so an absent subsystem read as `stale` ("gone quiet") and a botched install presented as a partially-live brain — issue #3 |

## Manual checks worth doing once

1. **Deliberately break a file.** Set `last_updated` on one subsystem to a week ago and rerun the generator. The subsystem should read `stale`, and the health summary should stop claiming a perfect score. If it still reads `active`, your timestamps are being rewritten somewhere and the gauge is lying.
2. **Delete a subsystem file.** The generator should report it as `missing`, not crash and not quietly drop it from the total.
3. **Read the aggregate as the agent.** Open `brain-state.json` and ask whether you would behave differently knowing it. If not, the values are decoration and the next step is the part of `SETUP-GUIDE.md` that cannot be automated.

## What a passing test does not prove

That the numbers mean anything. The kit is a set of meters; whether a meter is wired to something real is a property of your agent, not of this bundle. `SETUP-GUIDE.md` §6 lists the ways a passing install can still be inert.
