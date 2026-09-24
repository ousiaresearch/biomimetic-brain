---
name: mind-kit
description: "Give an agent internal state readings and a gate on them. Use when an agent should know how it is doing right now (energy, fatigue, circadian phase, attention, conflict, open questions), when a decision must be gated on measured inputs instead of a mood, or when state files have gone stale. Seeds 25 subsystem files, folds them into one brain-state.json, runs four maintenance passes, and refuses with a reason code that names the numbers behind it."
---

# The mind kit — meters, one aggregate, one gate

This package ships the scripts and the 25 subsystem state files. It does not decide anything by
itself: it reads and writes files, and reports `stale` rather than guessing. Your agent decides.

## Resolve the kit first

```bash
KIT="${PLUGIN_ROOT:-${HERMES_HOME:-$HOME/.hermes}/plugins/biomimetic-brain}"
ls "$KIT/scripts/generate-brain-state.py" || echo "kit not at $KIT — find it under $HERMES_HOME/plugins/"
```

Everything below runs from `$KIT`. Choose the directory that holds the agent's own state — the
scripts resolve it in this order: `--agent-dir`, then `$MIND_AGENT_DIR`, then `<kit>/agent`. Put it
inside the agent's existing home so state travels with the agent when it moves.

```bash
export MIND_AGENT_DIR="$HOME/agents/<your-agent>"
```

## 1. Seed, then produce the aggregate

```bash
mkdir -p "$MIND_AGENT_DIR/brain"
for f in $(find "$KIT/brain" -name '*.example.json'); do
  dest="$MIND_AGENT_DIR/brain/${f#$KIT/brain/}"; dest="${dest/.example/}"
  mkdir -p "$(dirname "$dest")"; cp "$f" "$dest"
done
python3 "$KIT/scripts/generate-brain-state.py"
python3 "$KIT/scripts/self_test.py"        # 11 checks, expect all green
```

`brain-state.json` is the contract. Anything that wants to know how the agent is doing reads that
one file, not 25. Every reading carries its age and the age it is allowed to reach, so a subsystem
that stopped updating reads `stale` instead of continuing to assert an old number.

**The shipped `*.example.json` files carry structure, not truth.** Seeding them and walking away
gives you a kit that reports values nobody observed. Fill them with what is actually true for this
agent — that step is the install, and it cannot be automated.

## 2. Keep it honest on a schedule

| Pass | Command | Cadence | What it fixes |
|---|---|---|---|
| Snapshot | `bash "$KIT/scripts/brain-snapshot.sh"` | hourly | regenerates the aggregate and keeps a one-line-per-subsystem history |
| Maintenance | `bash "$KIT/scripts/brain-maintenance.sh"` | every 4h | ages readings, flags past-max-age subsystems, writes the health log |
| Consistency | same script | with maintenance | cross-checks the aggregate against its sources and reports disagreement |
| Consolidation | `python3 "$KIT/scripts/consolidate-mind.py"` | daily | folds what actually happened back into state, so the files describe the day that occurred |

A state file nothing updates ages into fiction. If consolidation has not run, say so when you report
state rather than presenting yesterday's numbers as now.

## 3. Gate a decision on the numbers

```bash
python3 "$KIT/scripts/decision-gate.py"            # PROCEED
python3 "$KIT/scripts/decision-gate.py" --mode essential   # the heavier threshold set
```

Exit codes are the decision: **0 PROCEED**, **1 CAUTION**, **2 VETO**. The JSON on stdout names the
reason code and the inputs behind it, so a refusal can be traced to a number instead of read as a
mood. Run `python3 "$KIT/scripts/decision-gate_test.py"` to assert the exact reason code for every
documented rule.

Two properties to preserve when you wire it in:

- **The gate is read-only.** Gating a decision never mutates the state that produced it.
- **Defaults are labelled.** Any value it had to assume because a file was absent is reported as a
  default, never passed off as a reading.

## 4. Report state to a human honestly

State is a reading, not a feeling and not evidence of anything inner. When asked how you are, answer
from the aggregate and say what is stale; do not upgrade a number into a claim about experience.

## Pairs with

The Return Line (`hermes plugins install return-line`) carries `brain-state.json` into the live turn
without touching the system prompt — this kit produces the aggregate, that one makes the conversation
actually read it.

## If something is wrong

- **`FileNotFoundError: .../agent/brain-state.json`** — `MIND_AGENT_DIR` is unset and the default
  `<kit>/agent` does not exist. Set it, re-run.
- **Everything reads `missing`** — the subsystem files were never seeded; run step 1.
- **Everything reads `stale`** — the maintenance and consolidation passes are not scheduled.
- **The gate returns CAUTION on a quiet machine** — it falls back to the real clock when no circadian
  reading is present, and says so in `quiet_hours_source`.
