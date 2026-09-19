# NOTES — what this build adds

The published predecessor (`biomimetic-brain`) documents 22 subsystems. The build this kit ships is
25, and the scripts have moved on since publication. The differences, honestly labelled:

## Subsystems added since the published table

| Subsystem | Directory | What it adds |
|---|---|---|
| Habenula | `brain/habenula/` | Disappointment signal, distinct from low drive: what was expected and did not arrive. |
| Reticular formation | `brain/reticular/` | Arousal gating between sleep-adjacent quiet and full wakefulness. |
| Visual | `brain/visual/` | Recent visual evidence carried as state rather than as an attachment. |
| Decision log | `brain/decisions/` | What the gate decided and why, so a VETO can be audited after the fact. |
| Invariants | `brain/invariants.json` | Conditions that must hold across subsystems, checked by `brain-maintenance.sh`. |

`brain/_retired/` in the working tree holds files that are deliberately not read any more
(`*.never-invoked`, `*.prior-operator-era`). The kit ships none of them; the naming convention is
included here because it is the honest way to keep a dead monitor out of the gate without deleting
the evidence that it existed.

## Script movement

- `generate-brain-state.py` — 16.7 KB published, 19 KB here. Now reports per-subsystem `age_h` and
  `max_age_h` and a `health_summary`, which is what makes staleness visible rather than silent.
- `consolidate-mind.py` — not in the published tree at all. This is the pass that folds evidence
  into state; without it a state file ages into fiction.
- Everything reads the agent directory from `--agent-dir` / `$MIND_AGENT_DIR` / `./agent`. No name
  is assumed anywhere in the kit.
- The aggregate no longer carries a `migration` field naming anyone's history. That was ours, not
  the architecture's.

## What is deliberately not shipped

Live state values, the record directory, any log of what the agent actually did, and the operator's
own notes. The kit is the instrument, not our readings.
