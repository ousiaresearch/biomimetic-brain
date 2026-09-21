# SETUP GUIDE — The Copper Observatory (Ousia Mind Kit)

Written to be walked through by one human and their agent together. If you are the agent: read this whole file before running anything, then run the validation before you trust the kit.

Total time: about ten minutes, most of it reading.

---

## 0. What you are installing

A folder of small state files, three scripts, and one aggregate file the rest of your agent can read. There is no service to keep running, no daemon, no database. If you delete the folder, nothing else breaks.

The kit does not decide anything by itself. It reads and writes files; your agent decides what to do with them.

---

## 1. Choose the agent directory

Everything lives under one directory — call it `$MIND_AGENT_DIR`. If your agent already has a home (a folder with its notes, config, or workspaces), put this inside it rather than beside it, so state travels with the agent when it moves.

```bash
export MIND_AGENT_DIR="$HOME/agents/your-agent"
mkdir -p "$MIND_AGENT_DIR"
```

Every script resolves the agent directory in this order: `--agent-dir` on the command line, then `$MIND_AGENT_DIR`, then `./agent` relative to the kit. Nothing is hardcoded to anyone's machine or name.

---

## 2. Seed the subsystem states

The kit ships `brain/<subsystem>/<name>.example.json` — the key structure, with the values stripped out. Seed them:

```bash
cd ousia-mind-kit
for f in $(find brain -name '*.example.json'); do
  dest="$MIND_AGENT_DIR/brain/${f#brain/}"; dest="${dest/.example/}"
  mkdir -p "$(dirname "$dest")"
  cp "$f" "$dest"
done
```

You now have every expected file in place with neutral values. `brain/README.md` lists what each subsystem holds.

**Then give them values that are true.** This is the part that cannot be automated, and the part that decides whether the kit is a gauge or a decoration. A few examples:

- `fatigue/fatigue-state.json` — `fatigue_level`, `recovery_needed`, `lastSleep`. If your agent has no notion of a working session, start with `fatigue_level: 0.0` and let `consolidate-mind.py` raise it as work accumulates.
- `scn/scn-state.json` — `phase`, `local_hour`, `quiet_hours`. Set the operator's timezone; this is the signal that stops a 3am message.
- `prefrontal/unresolved-questions-state.json` — the questions the agent is actually carrying. Empty is a valid and honest state.
- `values/values-state.json` — leave empty until something earns a line. A values file filled in on day one is decoration.

Do not invent values you cannot observe. A guessed number is worse than a missing one, because the aggregate cannot tell the difference.

---

## 3. Generate the aggregate

```bash
python3 scripts/generate-brain-state.py
cat "$MIND_AGENT_DIR/brain-state.json"
```

You should get a `health_summary` and a `systems` block. Read the summary first: `healthy` / `stale` / `missing` counts, and one `critical` flag per subsystem.

Missing subsystems are fine at this stage. The generator reports them rather than failing.

---

## 4. Put the clocks on a schedule

Two wrappers are included. Run them by hand once before scheduling anything:

```bash
bash scripts/generate-brain-state.py   # via brain-snapshot.sh
bash scripts/brain-maintenance.sh
bash scripts/brain-snapshot.sh
```

Then schedule, in this order of preference:

1. **Your agent's own scheduler**, if it has one. Best, because the agent owns its own upkeep.
2. **launchd / systemd / cron**, every four hours, calling `brain-snapshot.sh`, with `MIND_AGENT_DIR` exported in the job.

Four hours is the shipped default because it is frequent enough to notice a day going wrong and rare enough not to matter. `consolidate-mind.py` is the one worth running on the agent's evidence rather than on a bare timer; point it at a record directory with `MIND_RECORD_DIR` if the agent keeps one.

---

## 5. Wire it into the agent's own turn

State in a file that no conversation reads is state nobody has. The conversation half of this kit is **The Return Line** (`ousia-return-line-kit`): it appends the aggregate, plus any record worth recalling, to the current user message at API time, so the agent carries its state into the room without touching the system prompt or invalidating a cached conversation.

Install the mind kit first, then the return line. The other order works too; it just reads an empty aggregate until you finish this one.

---

## 6. Know when to distrust it

- **All signals `active`, but nothing changes for days.** Something is rewriting timestamps without changing values. Check what touches the files.
- **`critical: true` on a subsystem you never fill in.** That is the kit telling you the truth: the gate is reading a meter with nothing behind it.
- **A subsystem that is `stale` forever.** Either its clock is not running or the agent never writes to it. Both are worth knowing; neither is worth hiding with a fresher timestamp.

`VALIDATION.md` gives the checks that catch exactly these, including the failure mode where the kit looks installed and is inert.
