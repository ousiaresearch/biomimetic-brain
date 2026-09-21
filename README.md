# Biomimetic Brain — a mind kit for AI agents

**Give your agent a body clock, a battery, and an honest sense of how it is doing.**

Most agents have no idea how they are. They answer the same way at 3am as at 10am, after ten hours of work or none. This kit changes that: it keeps a small set of internal readings that rise and fall on their own — energy, fatigue, motivation, novelty, time of day, attention, conflict, open questions — and folds them into one file your agent can read.

That file is called `brain-state.json`. Anything in your agent that wants to know *how it is doing right now* reads that one file.

```
somatic + fatigue + circadian + motivation + attention
                        ↓
                 ONE STATE FILE
                        ↓
              PROCEED / CAUTION / VETO
```

## What you get

- **25 subsystems, one small JSON file each.** Energy and tension, fatigue and recovery, motivation and novelty, circadian phase, attention, conflict, emotional tone, memory replay, values, open questions, and more. Each file is a few lines. None of them requires a model call.
- **One aggregate.** `generate-brain-state.py` folds all 25 into `brain-state.json`, with a health summary. That is the file the rest of your agent reads.
- **Staleness you can trust.** Every reading carries how old it is and how old it is allowed to be. A subsystem that has gone quiet reads as `stale` instead of quietly lying to you.
- **Fatigue that is not a light switch.** Recovery accumulates while your agent works, and an engagement override can *suspend* fatigue without erasing it. The override is recorded as an override, so you can see when the caffeine kicked in.
- **The four passes that keep it honest.** Snapshot, maintenance, consistency check, and a consolidation pass that folds what actually happened back into state. A state file nothing updates ages into fiction; this is the part that stops that.
- **A decision gate.** PROCEED, CAUTION, or VETO, from named inputs, so a refusal can be traced to the numbers that caused it rather than to a mood.
- **A self-test.** It builds a throwaway agent from scratch and proves the whole thing runs, so you are not trusting a README that has never executed.

## Install in five minutes

```bash
export MIND_AGENT_DIR=/path/to/your/agent
mkdir -p "$MIND_AGENT_DIR/brain"
# seed every subsystem file from the shipped examples
for f in $(find brain -name '*.example.json'); do
  dest="$MIND_AGENT_DIR/brain/${f#brain/}"; dest="${dest/.example/}"
  mkdir -p "$(dirname "$dest")"; cp "$f" "$dest"
done
python3 scripts/generate-brain-state.py       # writes $MIND_AGENT_DIR/brain-state.json
python3 scripts/self_test.py                  # 10 checks, expect all green
```

Then read [SETUP-GUIDE.md](SETUP-GUIDE.md), which walks a human and their agent through it in the order it has to happen — including the part that cannot be automated: giving the files values that are actually true.

## Half of a pair

This kit measures. To make the readings matter in conversation, install **[The Return Line](https://github.com/ousiaresearch/return-line)**, which appends the state file and relevant history to the live turn without touching the system prompt.

## The Ousia framing, kept short

Ousia Research builds agents that run for a long time rather than for one conversation. The discipline here is *receive, calibrate, repair, return*: read before deciding, keep an honest record, fix what drifted, and leave the work usable by whoever comes next. This kit is the receive-and-calibrate half, as software.

## What this is not

Not a personality, not a soul, and not evidence that anything is conscious. It is a set of meters, a fold, and a gate — cheap enough to run every hour on a laptop, and honest enough to say *stale* when it does not know.

## Files

```
brain/                      one state file per subsystem (*.example.json = structure only)
brain-state.example.json    the aggregate this kit produces
scripts/generate-brain-state.py   folds the subsystem files into the aggregate
scripts/consolidate-mind.py       folds evidence back into state on a schedule
scripts/brain-maintenance.sh      maintenance and consistency pass
scripts/brain-snapshot.sh         snapshot + aggregate on a schedule
scripts/self_test.py              builds a neutral agent and checks the kit actually runs
docs/                       architecture, decision gate, predictive processing
SETUP-GUIDE.md              install, step by step
VALIDATION.md               how to prove it works, and how a passing install can still be inert
NOTES.md                    what changed from the published 22-subsystem version
```

MIT licensed. See [LICENSE](LICENSE).
