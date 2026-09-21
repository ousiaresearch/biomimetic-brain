#!/usr/bin/env python3
"""
decision-gate.py — the decision gate the kit publishes in docs/DECISION_GATE.md ("Gate Logic (v4)").

    MIND_AGENT_DIR=/path/to/agent python3 scripts/decision-gate.py <decision-label> [mode]

mode is one of standard | low_scope | minimal | essential (default: standard). Only `essential`
changes a verdict: it bypasses quiet hours, as the spec says. The other three names are carried
through to the output so a caller can label the run; the rule set is identical.

One JSON object goes to stdout: the reason code, the verdict/scope, the adjusted confidence the
gate actually used, every named input it read, and which state files were missing or unreadable —
so a reader can tell a real reading from a default. A one-line human summary goes to stderr.

Exit codes, as annotated in the spec: PROCEED 0, VETO 1, CAUTION 2.

Read-only: nothing is written anywhere. Every input file is optional; an absent or unparseable
file is reported and replaced by a neutral default rather than crashing the gate.

Test seam: MIND_NOW=HH:MM (or --now HH:MM) pins the local clock and MIND_TZ=Area/City pins the
zone. Unset, the machine's real local clock is used. The seam exists because the quiet-hours
rules read the wall clock, and a test that cannot pin the clock cannot assert them.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _agent_path import agent_dir

AGENT = agent_dir()
BRAIN = str(AGENT / "brain")

# docs/DECISION_GATE.md: "Hours: 23:00-05:30 (from entrainment targetSchedule)".
QUIET_START_DEFAULT = 23.0   # 23:00 local
QUIET_END_DEFAULT = 5.5      # 05:30 local
# docs/DECISION_GATE.md: fall back to the real clock when SCN is >2h stale, and log a drift
# warning when SCN contradicts the real clock by more than 2 hours.
SCN_STALE_AFTER_H = 2.0
SCN_DRIFT_AFTER_H = 2.0
MODES = ("standard", "low_scope", "minimal", "essential")
EXIT_FOR = {"proceed": 0, "caution": 2, "veto": 1}

# Signal sources, in the order docs/DECISION_GATE.md lists them. Second candidates are the
# flat fallbacks the shipped generator also honours.
SOURCES_SPEC = [
    ("somatic", ["somatic/markers.json"]),
    ("fatigue", ["fatigue/fatigue-state.json"]),
    ("scn", ["scn/scn-state.json"]),
    ("attention", ["attention/attention-state.json"]),
    ("hypothalamus", ["hypothalamus/hypothalamus-state.json", "hypothalamus-state.json"]),
    ("basal-ganglia", ["basal-ganglia/habit-state.json"]),
    ("prefrontal", ["prefrontal/interest-emergence-state.json"]),
    ("vta", ["dopamine/vta-state.json"]),
    ("novelty", ["dopamine/novelty-state.json"]),
    ("predictive", ["predictive/surprise-log.json"]),
    ("entrainment", ["entrainment-state.json"]),
]

MISSING: list = []
UNREADABLE: list = []
WARNINGS: list = []
READ_SOURCES: dict = {}
STATUS_BY_SUBSYSTEM: dict = {}


# ── helpers ──────────────────────────────────────────────────────────────────

def parse_argv(argv):
    """`<decision-label> [mode]`, with --agent-dir/--now stripped wherever they appear."""
    label, mode, now_override, rest = None, "standard", None, []
    args, i = argv[1:], 0
    while i < len(args):
        a = args[i]
        if a in ("--agent-dir", "--now") and i + 1 < len(args):
            if a == "--now":
                now_override = args[i + 1]
            i += 2
            continue
        if a.startswith("--agent-dir="):
            i += 1
            continue
        if a.startswith("--now="):
            now_override = a.split("=", 1)[1]
            i += 1
            continue
        rest.append(a)
        i += 1
    if rest:
        label = rest[0]
    if len(rest) > 1:
        mode = rest[1]
    return (label or "manual_check"), mode, now_override


def num(value, default):
    """A float, or the default. Booleans and junk never leak into a reading."""
    if isinstance(value, bool) or value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def load(subsystem, rel_candidates):
    """Read the first file that exists. Records read/missing/unreadable, never raises."""
    for rel in rel_candidates:
        path = os.path.join(BRAIN, rel)
        if os.path.exists(path):
            try:
                with open(path) as fh:
                    data = json.load(fh)
                READ_SOURCES[rel] = "read"
                STATUS_BY_SUBSYSTEM[subsystem] = "read"
                return data if isinstance(data, dict) else {}
            except Exception:
                UNREADABLE.append("brain/" + rel)
                READ_SOURCES[rel] = "unreadable"
                STATUS_BY_SUBSYSTEM[subsystem] = "unreadable"
                return {}
    rel = rel_candidates[0]
    MISSING.append("brain/" + rel)
    READ_SOURCES[rel] = "missing"
    STATUS_BY_SUBSYSTEM[subsystem] = "missing"
    return {}


def resolve_now(override):
    """The local clock: real unless pinned. Returns (aware datetime, tz, source)."""
    now = datetime.now().astimezone()
    tzname = os.environ.get("MIND_TZ")
    if tzname:
        try:
            from zoneinfo import ZoneInfo
            now = datetime.now(ZoneInfo(tzname))
        except Exception:
            WARNINGS.append(f"MIND_TZ={tzname!r} is not a known zone; using the system local zone")
    if not override:
        return now, now.tzinfo, "system"
    text = str(override).strip()
    if "T" in text:
        try:
            dt = datetime.fromisoformat(text)
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=now.tzinfo)
            return dt, dt.tzinfo, "override"
        except ValueError:
            pass
    m = re.match(r"^(\d{1,2}):(\d{2})$", text)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        if 0 <= hour < 24 and 0 <= minute < 60:
            return now.replace(hour=hour, minute=minute, second=0, microsecond=0), now.tzinfo, "override"
    WARNINGS.append(f"could not parse MIND_NOW/--now={override!r}; using the real clock")
    return now, now.tzinfo, "system"


def age_hours(stamp, now):
    """Hours since an ISO timestamp, or None when there is no usable stamp."""
    if not stamp:
        return None
    try:
        dt = datetime.fromisoformat(str(stamp).replace("Z", "+00:00"))
    except ValueError:
        return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=now.tzinfo)
    return (now.astimezone(timezone.utc) - dt.astimezone(timezone.utc)).total_seconds() / 3600


def hour_of(value):
    """'23:00' | 23 | 23.5 | '23.5' -> hours past midnight, else None."""
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value) if 0 <= float(value) < 24 else None
    text = str(value).strip()
    m = re.match(r"^(\d{1,2}):(\d{2})$", text)
    if m:
        hour, minute = int(m.group(1)), int(m.group(2))
        if hour < 24 and minute < 60:
            return hour + minute / 60.0
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if 0 <= number < 24 else None


def hhmm(hours):
    total = int(round((hours % 24) * 60)) % 1440
    return f"{total // 60:02d}:{total % 60:02d}"


def hour_gap(a, b):
    diff = abs(a - b) % 24.0
    return min(diff, 24.0 - diff)


def in_window(hour, start, end):
    if start == end:
        return False
    if start > end:                      # window crosses midnight, e.g. 23:00 -> 05:30
        return hour >= start or hour < end
    return start <= hour < end


def quiet_window(entrainment):
    """(start, end, source) — the entrainment targetSchedule, else the documented 23:00-05:30."""
    blocks = []
    for key in ("targetSchedule", "target_schedule", "schedule", "quiet_hours", "quietHours"):
        value = entrainment.get(key)
        if isinstance(value, dict):
            blocks.append(value)
        elif isinstance(value, list):
            blocks.extend(x for x in value if isinstance(x, dict))
    for block in blocks:
        start = end = None
        for key in ("quiet_start", "quietStart", "start", "start_hour", "startHour", "from"):
            if start is None and key in block:
                start = hour_of(block[key])
        for key in ("quiet_end", "quietEnd", "end", "end_hour", "endHour", "to"):
            if end is None and key in block:
                end = hour_of(block[key])
        nested = block.get("quiet") if isinstance(block.get("quiet"), dict) else None
        if nested:
            for key in ("start", "from", "quiet_start"):
                if start is None and key in nested:
                    start = hour_of(nested[key])
            for key in ("end", "to", "quiet_end"):
                if end is None and key in nested:
                    end = hour_of(nested[key])
        if start is not None and end is not None:
            return start, end, "entrainment"
    return QUIET_START_DEFAULT, QUIET_END_DEFAULT, "default"


# ── the rule set ─────────────────────────────────────────────────────────────
# Verbatim from docs/DECISION_GATE.md "Gate Logic (v4)", in the order the document prints them.
# The document's own headings fix two placements: the habit bypass runs BEFORE the gut-based
# vetoes ("BASAL GANGLIA HABIT BYPASS (before gut-based veto)") and PROCEED EXTENDED is checked
# RIGHT AFTER VETO, before caution. Everything else follows the section order as written.

RULES = [
    # ── VETO (exit 1) — the non-gut vetoes, first, as printed ────────────────
    ("veto_recovery", "veto",
     lambda g: g["recovery_needed"]),
    ("veto_fatigue", "veto",
     lambda g: g["fatigue"] > 0.70),
    ("veto_low_arousal", "veto",
     lambda g: g["arousal"] < 0.30),
    ("veto_recovery_state", "veto",
     lambda g: g["drive"] == "recovery" and g["gut"] in ("pause", "stop")),

    # ── BASAL GANGLIA HABIT BYPASS (before the gut-based vetoes) ─────────────
    ("proceed_habit_gut_stop", "proceed",
     lambda g: g["strong_habit"] and g["gut"] == "stop"),
    ("proceed_habit_gut_pause", "proceed",
     lambda g: g["strong_habit"] and g["gut"] == "pause" and g["energy"] >= 0.20),
    ("proceed_habit_gut_doubt", "proceed",
     lambda g: g["strong_habit"] and g["gut"] == "doubt" and g["adj_confidence"] >= 0.30),

    # ── VETO (exit 1) — the gut-based vetoes ────────────────────────────────
    ("veto_gut_stop", "veto",
     lambda g: g["gut"] == "stop"),
    ("veto_distracted_pause", "veto",
     lambda g: g["distracted"] and g["gut"] == "pause"),
    ("veto_distracted_doubt", "veto",
     lambda g: g["distracted"] and g["gut"] == "doubt" and g["adj_confidence"] < 0.50),
    ("veto_pause_energy", "veto",
     lambda g: g["gut"] == "pause" and g["energy"] < 0.35),
    ("veto_doubt_confidence", "veto",
     lambda g: g["gut"] == "doubt" and g["adj_confidence"] < 0.40),
    ("veto_quiet_gut", "veto",
     lambda g: g["quiet_hours"] and g["gut"] in ("pause", "stop")),

    # ── PROCEED EXTENDED (exit 0) — right after VETO, before caution ────────
    ("proceed_passion", "proceed",
     lambda g: g["active_passions"] > 0),
    ("proceed_conviction", "proceed",
     lambda g: g["active_convictions"] > 0),
    ("proceed_curiosity_extended", "proceed",
     lambda g: g["emergent_interests"] > 0),
    ("proceed_extended_surge", "proceed",
     lambda g: g["novelty"] > 0.7 and g["vta"] > 0.7),
    ("proceed_novelty_extended", "proceed",
     lambda g: g["novelty"] > 0.7),
    ("proceed_vta_extended", "proceed",
     lambda g: g["vta"] > 0.7),

    # ── CAUTION (exit 2) — the last block, as printed ──────────────────────
    ("caution_distracted", "caution",
     lambda g: g["distracted"] and g["gut"] == "go_ahead"),
    ("caution_gut", "caution",
     lambda g: g["gut"] in ("pause", "wait")),
    ("caution_doubt", "caution",
     lambda g: g["gut"] == "doubt" and g["adj_confidence"] >= 0.40),
    ("caution_fatigue", "caution",
     lambda g: g["fatigue"] > 0.50),
    ("caution_low_arousal", "caution",
     lambda g: g["arousal"] < 0.50),
    ("caution_tension", "caution",
     lambda g: g["tension"] > 0.70),
    ("caution_quiet_hours", "caution",
     lambda g: g["quiet_hours"]),
]

# The named inputs each rule is decided on, so a refusal can be read back to its numbers.
RULE_INPUTS = {
    "veto_recovery": ("recovery_needed", "fatigue"),
    "veto_fatigue": ("fatigue",),
    "veto_low_arousal": ("arousal",),
    "veto_recovery_state": ("drive", "gut"),
    "proceed_habit_gut_stop": ("strong_habit", "habit_strength", "gut"),
    "proceed_habit_gut_pause": ("strong_habit", "habit_strength", "gut", "energy"),
    "proceed_habit_gut_doubt": ("strong_habit", "habit_strength", "gut", "adj_confidence"),
    "veto_gut_stop": ("gut", "tension"),
    "veto_distracted_pause": ("distracted", "gut", "energy"),
    "veto_distracted_doubt": ("distracted", "gut", "adj_confidence"),
    "veto_pause_energy": ("gut", "energy"),
    "veto_doubt_confidence": ("gut", "adj_confidence", "surprise_accuracy"),
    "veto_quiet_gut": ("quiet_hours", "gut"),
    "proceed_passion": ("active_passions",),
    "proceed_conviction": ("active_convictions",),
    "proceed_curiosity_extended": ("emergent_interests",),
    "proceed_extended_surge": ("novelty", "vta"),
    "proceed_novelty_extended": ("novelty", "gut"),
    "proceed_vta_extended": ("vta", "gut"),
    "caution_distracted": ("distracted", "gut", "confidence"),
    "caution_gut": ("gut", "energy", "fatigue"),
    "caution_doubt": ("gut", "adj_confidence"),
    "caution_fatigue": ("fatigue",),
    "caution_low_arousal": ("arousal",),
    "caution_tension": ("tension",),
    "caution_quiet_hours": ("quiet_hours", "real_local_hour"),
    "proceed": ("gut", "energy", "fatigue", "adj_confidence"),
}


def evaluate(g):
    for reason, verdict, cond in RULES:
        if cond(g):
            return reason, verdict
    return "proceed", "proceed"


def detail_for(reason, g):
    return ", ".join(f"{key}={g.get(key)}" for key in RULE_INPUTS.get(reason, ()))


# ── readings ─────────────────────────────────────────────────────────────────

def main():
    label, mode, now_override = parse_argv(sys.argv)
    now_override = now_override or os.environ.get("MIND_NOW")
    for bucket in (MISSING, UNREADABLE, WARNINGS, READ_SOURCES, STATUS_BY_SUBSYSTEM):
        bucket.clear()
    raw = {name: load(name, paths) for name, paths in SOURCES_SPEC}

    if mode not in MODES:
        WARNINGS.append(f"unknown mode {mode!r}; running the standard rule set")
        mode = "standard"

    now, tz, clock_source = resolve_now(now_override)
    real_local_hour = now.hour + now.minute / 60.0

    somatic = raw["somatic"]
    fatigue = raw["fatigue"]
    novelty_state = raw["novelty"]
    attention = raw["attention"]
    hypothalamus = raw["hypothalamus"]
    habit_state = raw["basal-ganglia"]
    prefrontal = raw["prefrontal"]
    surprise = raw["predictive"]
    scn = raw["scn"]
    entrainment = raw["entrainment"]

    # Somatic. A null gut_feeling is no signal, not a signal named None.
    gut = somatic.get("gut_feeling")
    gut = str(gut).strip().lower() if gut not in (None, "") else "neutral"
    energy = num(somatic.get("energy"), 0.5)
    confidence = num(somatic.get("confidence"), 0.5)
    tension = num(somatic.get("tension"), 0.0)
    valence = num(somatic.get("valence"), 0.5)

    # Fatigue
    fatigue_level = num(fatigue.get("fatigue_level"), 0.0)
    recovery_needed = bool(fatigue.get("recovery_needed", False))
    engagement_override = bool(fatigue.get("engagement_override", False))
    subsidy_active = bool(fatigue.get("subsidy_active", False))

    # Novelty + VTA drive
    novelty_seeking = num(novelty_state.get("novelty_seeking"), 0.5)
    vta = raw["vta"]
    vta_drive = num(vta.get("current_drive", vta.get("currentDrive", vta.get("drive"))), 0.57)

    # Prefrontal: emerged interests, convictions, passions. The spec names active_passions and
    # active_convictions but plain emergent_interests, so interests are counted as they stand.
    emerged = prefrontal.get("emerged_interests")
    emerged = emerged if isinstance(emerged, list) else []
    convictions = prefrontal.get("convictions")
    convictions = convictions if isinstance(convictions, list) else []
    passions = prefrontal.get("passions")
    passions = passions if isinstance(passions, list) else []

    def active(entries):
        return [e for e in entries if isinstance(e, dict) and str(e.get("status", "")).lower() == "active"]

    active_convictions = active(convictions)
    active_passions = active(passions)
    active_interests = [i for i in emerged
                        if isinstance(i, dict)
                        and str(i.get("status", "")).lower() == "active"
                        and str(i.get("urgency", "")).lower() in ("high", "medium")]

    # Attention
    attention_mode = attention.get("mode")
    attention_mode = str(attention_mode).strip().lower() if attention_mode else "unknown"
    distracted = attention_mode == "distracted"

    # Hypothalamus
    arousal = num(hypothalamus.get("arousal_level", hypothalamus.get("arousal")), 0.5)
    drive = hypothalamus.get("drive_state", hypothalamus.get("drive"))
    drive = str(drive).strip().lower() if drive not in (None, "") else "unknown"

    # Basal ganglia habits. The shipped habit-state.json carries a `habits` list; a `patterns`
    # map is read too, because both shapes are in the wild.
    habits = habit_state.get("habits")
    habits = habits if isinstance(habits, list) else []
    patterns = habit_state.get("patterns")
    if not habits and isinstance(patterns, dict):
        for name, value in patterns.items():
            if isinstance(value, dict):
                habits.append({**value, "pattern": value.get("pattern", name)})
            elif isinstance(value, (int, float)):
                habits.append({"pattern": name, "strength": value, "status": "active"})
    usable = [h for h in habits
              if isinstance(h, dict) and str(h.get("status", "active")).lower() in ("active", "forming")]
    habit_strength = max([num(h.get("strength"), 0.0) for h in usable], default=0.0)
    strong_habit = habit_strength >= 0.7

    # Surprise accuracy -> metacognitive confidence, before any doubt rule reads it.
    raw_stats = surprise.get("stats")
    stats = raw_stats if isinstance(raw_stats, dict) else {}
    surprise_accuracy = num(stats.get("accuracy_rate"), 0.5)
    conf_adj = (surprise_accuracy - 0.5) * 0.3
    adj_confidence = max(0.1, min(0.99, confidence + conf_adj))

    # ── Quiet hours: the real local clock is ground truth ──────────────────
    quiet_start, quiet_end, window_source = quiet_window(entrainment)
    real_quiet = in_window(real_local_hour, quiet_start, quiet_end)

    scn_phase = scn.get("phase")
    scn_phase = str(scn_phase).strip().lower() if scn_phase else "unknown"
    scn_says_quiet = scn_phase == "night" or bool(scn.get("quiet_hours", False))
    scn_hour = hour_of(scn.get("local_hour", scn.get("localHour", scn.get("hour"))))
    scn_stamp = scn.get("lastUpdated")
    scn_age = age_hours(scn_stamp, now)
    scn_fresh = scn_age is not None and scn_age <= SCN_STALE_AFTER_H
    scn_drift = scn_hour is not None and hour_gap(scn_hour, real_local_hour) > SCN_DRIFT_AFTER_H

    if not scn:
        WARNINGS.append("no SCN reading (brain/scn/scn-state.json); using the real clock for quiet hours")
    elif not scn_fresh:
        age_note = "no lastUpdated" if scn_age is None else f"{scn_age:.1f}h old"
        WARNINGS.append(f"SCN phase stale ({age_note}); using the real clock for quiet hours "
                        f"({hhmm(real_local_hour)})")
    elif scn_drift:
        WARNINGS.append(f"SCN drift: SCN reads {hhmm(scn_hour)} but the real clock reads "
                        f"{hhmm(real_local_hour)} (>2h apart); using the real clock")

    if scn and scn_fresh and not scn_drift:
        quiet_hours_raw = scn_says_quiet or real_quiet   # real clock stays ground truth
        quiet_source = "scn" if scn_says_quiet else ("scn+real_clock" if real_quiet else "scn")
    else:
        quiet_hours_raw = real_quiet
        quiet_source = "real_clock"

    essential = mode == "essential"
    quiet_hours = quiet_hours_raw and not essential
    if essential and quiet_hours_raw:
        WARNINGS.append("MODE=essential: quiet hours bypassed")

    g = {
        # doc tokens first, then the readings behind them
        "recovery_needed": recovery_needed,
        "fatigue": fatigue_level,
        "arousal": arousal,
        "drive": drive,
        "gut": gut,
        "distracted": distracted,
        "adj_confidence": adj_confidence,
        "energy": energy,
        "tension": tension,
        "novelty": novelty_seeking,
        "vta": vta_drive,
        "strong_habit": strong_habit,
        "habit_strength": habit_strength,
        "active_passions": len(active_passions),
        "active_convictions": len(active_convictions),
        "emergent_interests": len(emerged),
        "surprise_accuracy": surprise_accuracy,
        "quiet_hours": quiet_hours,
        "real_local_hour": round(real_local_hour, 4),
        "confidence": confidence,
    }

    reason, verdict = evaluate(g)

    out = {
        "decision": label,
        "mode": mode,
        "reason": reason,
        "verdict": verdict,
        "scope": verdict,
        "exit_code": EXIT_FOR[verdict],
        "adj_confidence": round(adj_confidence, 4),
        "confidence": confidence,
        "conf_adj": round(conf_adj, 4),
        "surprise_accuracy": surprise_accuracy,
        "essential": essential,
        "quiet_hours": quiet_hours,
        "quiet_hours_raw": quiet_hours_raw,
        "quiet_hours_source": quiet_source,
        "quiet_hours_scn_says": scn_says_quiet,
        "quiet_hours_window": {"start": hhmm(quiet_start), "end": hhmm(quiet_end),
                               "source": window_source},
        "real_local_hour": round(real_local_hour, 4),
        "clock": {
            "now": now.isoformat(),
            "timezone": str(tz),
            "source": clock_source,
        },
        "inputs": g,
        # Read, but named by no rule in "Gate Logic (v4)", so they gate nothing. The reference
        # implementation does use them (an engagement override suspends the recovery veto, a
        # subsidy splits caution_fatigue); the published rule set does not, so they are reported
        # here rather than quietly influencing a verdict.
        "read_not_gated": {
            "valence": valence,
            "engagement_override": engagement_override,
            "subsidy_active": subsidy_active,
        },
        "triggered_by": {key: g[key] for key in RULE_INPUTS.get(reason, ())},
        "detail": f"{reason}: {detail_for(reason, g)}",
        # Which readings came off disk and which are defaults: a value behind a missing file
        # is a default, and a reader has to be able to tell the two apart.
        "real_readings": [name for name, _ in SOURCES_SPEC
                          if STATUS_BY_SUBSYSTEM.get(name) == "read"],
        "defaulted_readings": [name for name, _ in SOURCES_SPEC
                               if STATUS_BY_SUBSYSTEM.get(name) != "read"],
        "sources": {rel: {"status": status} for rel, status in sorted(READ_SOURCES.items())},
        "missing_state_files": MISSING,
        "unreadable_state_files": UNREADABLE,
        "warnings": WARNINGS,
        "timestamp": now.isoformat(),
    }

    print(json.dumps(out, indent=2))
    print(f"{verdict.upper()} (exit {EXIT_FOR[verdict]}): {out['detail']}", file=sys.stderr)
    for warning in WARNINGS:
        print(f"warning: {warning}", file=sys.stderr)
    return EXIT_FOR[verdict]


if __name__ == "__main__":
    raise SystemExit(main())
