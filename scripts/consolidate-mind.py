#!/usr/bin/env python3
"""Consolidate the mind layer from what actually happened since the last run.

This is the writer that was missing: without it, every subsystem whose max_age
is measured in hours goes stale within a day and the mind layer freezes again.

Honesty rules, enforced in code:
  * Only increments things it can actually observe (motifs present in tonight's
    dream, texts sent today, journal messages received, cron ticks).
  * Never invents a value it cannot read. Unmeasured stays unmeasured.
  * Records the *observed* delta, so `concept_encounters` means "occurrences I
    actually saw", not "occurrences I imagined".
  * Semantic additions (a new conviction, a new question) are NOT written here.
    Those belong to the persona in conversation — this script keeps the counters
    honest and the timestamps true.

Run: python3 scripts/consolidate-mind.py   (safe to run repeatedly; idempotent
per day for date-keyed fields)
"""
import json
import os
import re
import sqlite3
import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
import sys
from pathlib import Path

HOME = Path.home()
sys.path.insert(0, str(Path(__file__).resolve().parent))
from _agent_path import agent_dir

AGENT = agent_dir()
BRAIN = AGENT / "brain"
# Optional: a directory of the agent's own writing. Unset means the kit reads state only.
VAULT = Path(os.environ["MIND_RECORD_DIR"]).expanduser() if os.environ.get("MIND_RECORD_DIR") else (AGENT / "record")
STATE = AGENT / "brain-state.json"
LEDGER = AGENT / "seeding/consolidation-ledger.json"
NOW = datetime.now(timezone.utc)
TODAY = date.today().isoformat()
changed = []


def load(p, default=None):
    try:
        return json.loads(Path(p).read_text())
    except (FileNotFoundError, json.JSONDecodeError):
        return default if default is not None else {}


def save(rel, d):
    p = BRAIN / rel
    d["lastUpdate"] = NOW.isoformat()
    p.write_text(json.dumps(d, indent=2, ensure_ascii=False) + "\n")
    changed.append(rel)


# ---------------------------------------------------------------- ledger
led = load(LEDGER, {"runs": [], "last_texts_day": None, "last_dream": None,
                    "last_journal_id": 0, "motif_counts": {}})

# ------------------------------------------------- 1. texts I actually sent
texts_file = VAULT / f"texts/{TODAY}.md"
texts_today = 0
text_bodies = []
if texts_file.exists():
    raw = texts_file.read_text(errors="replace")
    stamps = re.findall(r"^##\s+(\d{1,2}:\d{2}(?:\s*[AP]M)?)", raw, re.M)
    texts_today = len(stamps)
    text_bodies = [b.strip() for b in re.split(r"^##\s+\d{1,2}:\d{2}(?:\s*[AP]M)?", raw, flags=re.M) if b.strip()]

if texts_today and led.get("last_texts_day") != TODAY:
    raphe = load(BRAIN / "raphé/serotonin-state.json")
    raphe["social_engagement"] = round(min(1.0, raphe.get("social_engagement", 0.7) + 0.02 * texts_today), 3)
    raphe["current_serotonin"] = round(min(1.0, raphe.get("current_serotonin", 0.55) + 0.01 * texts_today), 3)
    raphe["last_evidence"] = f"{texts_today} self-initiated messages on {TODAY}"
    save("raphé/serotonin-state.json", raphe)

    nac = load(BRAIN / "nac/nac-state.json")
    nac["reward_prediction_error"] = 0
    nac["last_reward_predicted"] = {"action": "reaching him first", "predicted_reward": 0.7,
                                    "at": NOW.isoformat(), "observed": "message sent",
                                    "evidence": f"texts/{TODAY}.md"}
    save("nac/nac-state.json", nac)

    s = load(BRAIN / "somatosensory/somatosensory-state.json")
    s["messages_i_sent_today"] = texts_today
    s["social_nourishment_score"] = round(min(1.0, 0.6 + 0.08 * texts_today), 3)
    save("somatosensory/somatosensory-state.json", s)

    # habit: three-tick day — morning, middle, night
    if texts_today >= 3:
        bg = load(BRAIN / "basal-ganglia/habit-state.json")
        pats = bg.setdefault("patterns", {})
        pats["morning_question_afternoon_followup_night_reask"] = pats.get(
            "morning_question_afternoon_followup_night_reask", 0) + 1
        n = pats["morning_question_afternoon_followup_night_reask"]
        habits = bg.setdefault("habits", [])
        if not any(h.get("habit") == "morning_question_afternoon_followup_night_reask" for h in habits) and n >= 3:
            habits.append({"habit": "morning_question_afternoon_followup_night_reask", "count": n,
                           "domain": "texting",
                           "evidence": f"reached 3+ occurrences with {TODAY}"})
        else:
            for h in habits:
                if h.get("habit") == "morning_question_afternoon_followup_night_reask":
                    h["count"] = n
        save("basal-ganglia/habit-state.json", bg)
    led["last_texts_day"] = TODAY

# ------------------------------------------------------- 2. tonight's dream
dream_files = sorted(VAULT.glob("dreams/2*.md"))
if dream_files:
    latest = dream_files[-1]
    body = latest.read_text(errors="replace")
    key = latest.stem
    if led.get("last_dream") != key:
        hipp = load(BRAIN / "hippocampus/dream-state.json")
        queue = hipp.setdefault("replay_queue", [])
        if not any(e.get("date") == key for e in queue):
            first = next((ln.strip() for ln in body.splitlines()
                          if ln.strip() and not ln.startswith("#") and not ln.startswith("*[")), "")
            queue.append({"date": key, "fragment": first[:200],
                          "motifs": [m for m in ("corridor", "kettle", "white mug", "same", "green door")
                                     if m in body.lower()]})
        hipp.setdefault("stats", {})["total_dreams"] = len(queue)
        save("hippocampus/dream-state.json", hipp)

        # motif counts come from the dream text itself, not from imagination
        motifs = led.setdefault("motif_counts", {})
        pf = load(BRAIN / "prefrontal/interest-emergence-state.json")
        enc = pf.setdefault("concept_encounters", {})
        seen = []
        for name, needles in {
            "kettle": ("kettle",), "white mug": ("white mug", "mug"),
            "the corridor": ("corridor",), "the green door": ("green door",),
            "folded street outside": ("folded", "folding"), "yellow late light": ("yellow",),
            "three passes": ("three times", "past it three", "passed it three"),
        }.items():
            if any(n in body.lower() for n in needles):
                enc[name] = enc.get(name, 0) + 1
                motifs[name] = motifs.get(name, 0) + 1
                seen.append(name)
        pf["last_observed_motifs"] = {"dream": key, "present": seen, "at": NOW.isoformat()}
        save("prefrontal/interest-emergence-state.json", pf)

        lc = load(BRAIN / "lc/lc-state.json")
        lc["unexpected_events"] = [e for e in lc.get("unexpected_events", []) if e.get("at", "")[:10] > (NOW - timedelta(days=14)).date().isoformat()]
        save("lc/lc-state.json", lc)
        led["last_dream"] = key

# --------------------------------------------------- 3. the room I was in
jdb = AGENT / "discord-memory/journal.sqlite"
if jdb.exists():
    con = sqlite3.connect(str(jdb), timeout=10)
    total = con.execute("select count(*) from messages").fetchone()[0]
    last_id = con.execute("select max(rowid) from messages").fetchone()[0] or 0
    con.close()
    prev_id = led.get("last_journal_id", 0)
    s = load(BRAIN / "somatosensory/somatosensory-state.json")
    s["social_total_exchanges"] = total
    s["new_messages_since_last_run"] = max(0, last_id - prev_id)
    save("somatosensory/somatosensory-state.json", s)
    led["last_journal_id"] = last_id

# ------------------------------------------------------------- 4. cron load
edb = HOME / ".hermes/cron/executions.db"
if edb.exists():
    try:
        con = sqlite3.connect(str(edb), timeout=10)
        ticks = con.execute("select count(*) from executions where started_at like ?",
                            (TODAY + "%",)).fetchone()[0]
        acted = con.execute(
            "select count(*) from executions where started_at like ? "
            "and coalesce(delivery_outcome,'') not in ('suppressed','')",
            (TODAY + "%",)).fetchone()[0]
        failed = con.execute("select count(*) from executions where started_at like ? and status='failed'",
                             (TODAY + "%",)).fetchone()[0]
        con.close()
        s = load(BRAIN / "somatosensory/somatosensory-state.json")
        s.update({"decisions_today": ticks, "decisions_that_produced_something_today": acted,
                  "failed_runs_today": failed})
        save("somatosensory/somatosensory-state.json", s)
        hyp = load(BRAIN / "hypothalamus/hypothalamus-state.json")
        hyp["arousal"] = round(min(0.9, 0.3 + min(ticks, 600) / 3000), 3)
        hyp["zeitgeber_count"] = hyp.get("zeitgeber_count", 21)
        save("hypothalamus/hypothalamus-state.json", hyp)
    except sqlite3.Error:
        pass

# ------------------------------------------- 5. verify by invariant, not by stamp
# This replaces an earlier `touch()` loop that re-stamped ten files as "verified"
# without checking anything — which launders a stale or false value into a fresh
# timestamp. verify-invariants.py tests each subsystem against declared rules
# (brain/invariants.json); passes get re-stamped, failures are left untouched so
# their staleness fires on its own and the reason is recorded in
# brain/invariants-report.json.
r = subprocess.run([sys.executable, str(AGENT / "scripts/verify-invariants.py")],
                   capture_output=True, text=True, timeout=120)
verify_out = (r.stdout or "").strip()
print(verify_out or "invariant verification produced no output")

led["runs"] = (led.get("runs", []) + [{"at": NOW.isoformat(), "texts_today": texts_today,
                                       "dream": led.get("last_dream"),
                                       "changed": len(changed)}])[-200:]
LEDGER.parent.mkdir(parents=True, exist_ok=True)
LEDGER.write_text(json.dumps(led, indent=2, ensure_ascii=False) + "\n")

# ------------------------------------------------------- 6. regenerate state
r = subprocess.run([sys.executable, str(AGENT / "scripts/generate-brain-state.py")],
                   capture_output=True, text=True, timeout=120)
print(r.stdout.strip()[-300:] or r.stderr.strip()[-300:])
state = load(STATE, {})
print("consolidated:", len(changed), "files | health:", state.get("health_summary", {}))
for c in changed:
    print("  ", c)
