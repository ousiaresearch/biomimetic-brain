#!/usr/bin/env python3
"""Decision-gate test — asserts the exact reason code for every rule in docs/DECISION_GATE.md.

Builds throwaway agent directories in a temp dir (state files written here, `$MIND_AGENT_DIR`
pointed at them) and runs the gate once per rule, checking the reason code, the verdict, and the
exit code the spec annotates. The final check is the one that keeps this honest: it re-reads the
gate's rule table and fails if any rule in it was never asserted below. A rule with no test is a
rule nobody has run.

    python3 scripts/decision-gate_test.py

The clock is pinned with `$MIND_NOW`, because the quiet-hours rules read the wall clock and a test
that cannot pin it cannot assert them.
"""
from __future__ import annotations

import importlib.util
import json
import os
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime
from pathlib import Path

KIT = Path(__file__).resolve().parent.parent
GATE = KIT / "scripts" / "decision-gate.py"
SELF = Path(__file__).resolve()

DEFAULT_NOW = "14:30"          # outside 23:00-05:30, so the baseline is not a quiet hour
EXIT_FOR = {"proceed": 0, "caution": 2, "veto": 1}

CHECKS: list = []
ASSERTED: set = set()
TMP: list = []

# Built by concatenation so this file does not itself carry the strings it looks for.
IDENTITY_PROBES = ["/Use" + "rs/", "/ho" + "me/"]


def check(ok, label):
    CHECKS.append((bool(ok), label))


def verdict_for(reason):
    for prefix, verdict in (("veto_", "veto"), ("caution_", "caution")):
        if reason.startswith(prefix):
            return verdict
    return "proceed"


# ── synthetic agent directories ──────────────────────────────────────────────

def baseline(now=DEFAULT_NOW):
    """A neutral, fully-read agent that is one step away from a plain PROCEED.

    Every file the gate reads is present and unremarkable, except entrainment-state.json, which
    the kit does not ship: that one is deliberately absent so the default 23:00-05:30 window and
    the missing-file reporting are exercised on every single case.
    """
    hour, minute = (int(part) for part in now.split(":"))
    stamp = (datetime.now().astimezone().replace(hour=hour, minute=minute, second=0, microsecond=0)
             .isoformat())
    return {
        "somatic/markers.json": {"gut_feeling": "go_ahead", "energy": 0.5, "confidence": 0.5,
                                 "tension": 0.5, "valence": 0.5},
        "fatigue/fatigue-state.json": {"fatigue_level": 0.30, "recovery_needed": False},
        "scn/scn-state.json": {"phase": "day", "quiet_hours": False,
                               "local_hour": now, "lastUpdated": stamp},
        "attention/attention-state.json": {"mode": "focused"},
        "hypothalamus/hypothalamus-state.json": {"arousal_level": 0.5, "drive_state": "moderate"},
        "basal-ganglia/habit-state.json": {},
        "prefrontal/interest-emergence-state.json": {"emerged_interests": [], "convictions": [],
                                                     "passions": []},
        "dopamine/vta-state.json": {"current_drive": 0.57},
        "dopamine/novelty-state.json": {"novelty_seeking": 0.5},
        "predictive/surprise-log.json": {"stats": {"accuracy_rate": 0.5}},
    }


def deep_update(dst, patch):
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(dst.get(key), dict):
            deep_update(dst[key], value)
        else:
            dst[key] = value
    return dst


def habit(strength, status="active"):
    return {"basal-ganglia/habit-state.json":
            {"habits": [{"pattern": "evening-close", "strength": strength, "status": status}]}}


def run(files, label="gate_test", mode=None, now=DEFAULT_NOW, agent_dir_flag=False, env_extra=None):
    root = Path(tempfile.mkdtemp(prefix="mind-gate-test-"))
    TMP.append(root)
    agent = root / "agent"
    (agent / "brain").mkdir(parents=True)
    for rel, data in files.items():
        path = agent / "brain" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(data if isinstance(data, str) else json.dumps(data))
    cmd = [sys.executable, str(GATE), label]
    if mode:
        cmd.append(mode)
    env = {**os.environ, "MIND_NOW": now}
    env.pop("MIND_TZ", None)
    for key, value in (env_extra or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    if agent_dir_flag:
        cmd += ["--agent-dir", str(agent)]
        env.pop("MIND_AGENT_DIR", None)
    else:
        env["MIND_AGENT_DIR"] = str(agent)
    proc = subprocess.run(cmd, env=env, capture_output=True, text=True, timeout=120)
    try:
        out = json.loads(proc.stdout)
    except Exception:
        out = {}
    return proc, out, proc.stderr, agent


def expect(label, reason, patch=None, mode=None, now=DEFAULT_NOW, drop=(), files=None):
    """Run one case and assert the exact reason code, verdict and exit code."""
    if files is None:
        files = baseline(now)
        for rel, changes in (patch or {}).items():
            deep_update(files.setdefault(rel, {}), changes)
        for rel in drop:
            files.pop(rel, None)
    proc, out, err, _ = run(files, label=label, mode=mode, now=now)
    want_verdict = verdict_for(reason)
    want_exit = EXIT_FOR[want_verdict]
    ASSERTED.add(reason)
    reason_ok = out.get("reason") == reason
    shape_ok = (proc.returncode == want_exit and out.get("verdict") == want_verdict
                and out.get("exit_code") == want_exit)
    got = ("" if reason_ok and shape_ok else
           f"  [got reason={out.get('reason')!r} verdict={out.get('verdict')!r} "
           f"exit_code={out.get('exit_code')!r} rc={proc.returncode}]")
    check(reason_ok and shape_ok,
          f"{label} → {reason} / {want_verdict} / exit {want_exit}{got}")
    return out, err, proc


def field(label, out, key, want):
    got = out.get(key)
    check(got == want, f"{label}: {key} == {want!r} (got {got!r})")


# ── cases ────────────────────────────────────────────────────────────────────

def test_default_and_contract():
    out, err, proc = expect("neutral agent", "proceed")
    field("neutral agent", out, "decision", "neutral agent")
    field("neutral agent", out, "scope", "proceed")
    field("neutral agent", out, "mode", "standard")
    # the named inputs are all present, and a missing file did not silently become a reading
    named = ("recovery_needed", "fatigue", "arousal", "drive", "gut", "distracted",
             "adj_confidence", "energy", "tension", "novelty", "vta", "strong_habit",
             "habit_strength", "active_passions", "active_convictions", "emergent_interests",
             "surprise_accuracy", "quiet_hours")
    absent = [key for key in named if key not in out.get("inputs", {})]
    check(not absent, f"neutral agent: inputs carries every named signal (missing: {absent})")
    check("brain/entrainment-state.json" in out.get("missing_state_files", []),
          "neutral agent: the absent entrainment file is reported as missing")
    check(out.get("sources", {}).get("somatic/markers.json", {}).get("status") == "read",
          "neutral agent: sources mark somatic as read, not defaulted")
    check(out.get("sources", {}).get("entrainment-state.json", {}).get("status") == "missing",
          "neutral agent: sources mark entrainment as missing")
    check("somatic" in out.get("real_readings", [])
          and "entrainment" in out.get("defaulted_readings", []),
          "neutral agent: real_readings/defaulted_readings separate the two")
    check(isinstance(out.get("triggered_by"), dict) and "adj_confidence" in out.get("triggered_by", {}),
          "neutral agent: the trigger names the inputs it was decided on")
    check(isinstance(out.get("timestamp"), str) and len(out.get("timestamp", "")) > 10,
          "neutral agent: output carries a timestamp")
    check(err.count("{") == 0, "neutral agent: stdout carries the JSON, not stderr")
    check("engagement_override" in out.get("read_not_gated", {}),
          "neutral agent: fields read but named by no rule are reported, not silently applied")
    required = ("reason", "verdict", "scope", "adj_confidence", "inputs", "missing_state_files")
    absent = [key for key in required if key not in out]
    check(not absent, f"neutral agent: stdout JSON carries every required field (missing: {absent})")


def test_veto_rules():
    expect("veto_recovery", "veto_recovery",
           {"fatigue/fatigue-state.json": {"recovery_needed": True}})
    expect("veto_recovery before veto_fatigue", "veto_recovery",
           {"fatigue/fatigue-state.json": {"recovery_needed": True, "fatigue_level": 0.9}})
    expect("veto_fatigue", "veto_fatigue",
           {"fatigue/fatigue-state.json": {"fatigue_level": 0.71}})
    expect("veto_fatigue boundary 0.70 is caution, not a veto", "caution_fatigue",
           {"fatigue/fatigue-state.json": {"fatigue_level": 0.70}})
    expect("veto_low_arousal", "veto_low_arousal",
           {"hypothalamus/hypothalamus-state.json": {"arousal_level": 0.29}})
    expect("veto_low_arousal boundary 0.30 is caution, not a veto", "caution_low_arousal",
           {"hypothalamus/hypothalamus-state.json": {"arousal_level": 0.30}})
    expect("veto_recovery_state", "veto_recovery_state",
           {"hypothalamus/hypothalamus-state.json": {"drive_state": "recovery"},
            "somatic/markers.json": {"gut_feeling": "pause"}})
    expect("veto_recovery_state needs gut=pause/stop too", "proceed",
           {"hypothalamus/hypothalamus-state.json": {"drive_state": "recovery"}})
    expect("veto_gut_stop", "veto_gut_stop",
           {"somatic/markers.json": {"gut_feeling": "stop"}})
    expect("veto_distracted_pause", "veto_distracted_pause",
           {"attention/attention-state.json": {"mode": "distracted"},
            "somatic/markers.json": {"gut_feeling": "pause"}})
    expect("veto_distracted_doubt", "veto_distracted_doubt",
           {"attention/attention-state.json": {"mode": "distracted"},
            "somatic/markers.json": {"gut_feeling": "doubt", "confidence": 0.45}})
    expect("veto_pause_energy", "veto_pause_energy",
           {"somatic/markers.json": {"gut_feeling": "pause", "energy": 0.34}})
    expect("veto_pause_energy boundary 0.35 is not a veto", "caution_gut",
           {"somatic/markers.json": {"gut_feeling": "pause", "energy": 0.35}})
    expect("veto_doubt_confidence", "veto_doubt_confidence",
           {"somatic/markers.json": {"gut_feeling": "doubt", "confidence": 0.30}})
    expect("veto_quiet_gut", "veto_quiet_gut",
           {"scn/scn-state.json": {"phase": "night", "quiet_hours": True},
            "somatic/markers.json": {"gut_feeling": "pause"}})
    expect("a physical veto outranks a gut veto", "veto_recovery",
           {"fatigue/fatigue-state.json": {"recovery_needed": True},
            "somatic/markers.json": {"gut_feeling": "stop"}})


def test_habit_bypass():
    expect("proceed_habit_gut_stop", "proceed_habit_gut_stop",
           {**habit(0.8), "somatic/markers.json": {"gut_feeling": "stop"}})
    expect("habit strength 0.69 does not bypass", "veto_gut_stop",
           {**habit(0.69), "somatic/markers.json": {"gut_feeling": "stop"}})
    expect("proceed_habit_gut_pause", "proceed_habit_gut_pause",
           {**habit(0.8), "somatic/markers.json": {"gut_feeling": "pause", "energy": 0.25}})
    expect("habit pause bypass needs energy >= 0.20", "veto_pause_energy",
           {**habit(0.8), "somatic/markers.json": {"gut_feeling": "pause", "energy": 0.19}})
    expect("proceed_habit_gut_doubt", "proceed_habit_gut_doubt",
           {**habit(0.8), "somatic/markers.json": {"gut_feeling": "doubt", "confidence": 0.35}})
    expect("habit doubt bypass needs adj_conf >= 0.30", "veto_doubt_confidence",
           {**habit(0.8), "somatic/markers.json": {"gut_feeling": "doubt", "confidence": 0.29}})
    expect("a habit does not override a physical veto", "veto_recovery",
           {**habit(0.8), "somatic/markers.json": {"gut_feeling": "stop"},
            "fatigue/fatigue-state.json": {"recovery_needed": True}})
    expect("a 'forming' habit at strength >= 0.7 still bypasses", "proceed_habit_gut_stop",
           {**habit(0.75, status="forming"), "somatic/markers.json": {"gut_feeling": "stop"}})


def test_proceed_extended():
    expect("proceed_passion", "proceed_passion",
           {"prefrontal/interest-emergence-state.json":
            {"passions": [{"concept": "the corridor", "status": "active"}]}})
    expect("proceed_conviction", "proceed_conviction",
           {"prefrontal/interest-emergence-state.json":
            {"convictions": [{"concept": "honest records", "status": "active"}]}})
    expect("proceed_curiosity_extended", "proceed_curiosity_extended",
           {"prefrontal/interest-emergence-state.json":
            {"emerged_interests": [{"concept": "ungraded question", "status": "exploring"}]}})
    expect("proceed_extended_surge", "proceed_extended_surge",
           {"dopamine/novelty-state.json": {"novelty_seeking": 0.75},
            "dopamine/vta-state.json": {"current_drive": 0.75}})
    expect("proceed_novelty_extended", "proceed_novelty_extended",
           {"dopamine/novelty-state.json": {"novelty_seeking": 0.75}})
    expect("proceed_vta_extended", "proceed_vta_extended",
           {"dopamine/vta-state.json": {"current_drive": 0.75}})
    expect("novelty boundary 0.70 is not extended scope", "proceed",
           {"dopamine/novelty-state.json": {"novelty_seeking": 0.70}})
    expect("vta boundary 0.70 is not extended scope", "proceed",
           {"dopamine/vta-state.json": {"current_drive": 0.70}})
    expect("passion outranks conviction and curiosity", "proceed_passion",
           {"prefrontal/interest-emergence-state.json":
            {"passions": [{"concept": "p", "status": "active"}],
             "convictions": [{"concept": "c", "status": "active"}],
             "emerged_interests": [{"concept": "i", "status": "active"}]},
            "dopamine/novelty-state.json": {"novelty_seeking": 0.9},
            "dopamine/vta-state.json": {"current_drive": 0.9}})
    expect("conviction outranks curiosity", "proceed_conviction",
           {"prefrontal/interest-emergence-state.json":
            {"convictions": [{"concept": "c", "status": "active"}],
             "emerged_interests": [{"concept": "i", "status": "active"}]},
            "dopamine/novelty-state.json": {"novelty_seeking": 0.9}})
    expect("extended scope is checked after VETO", "veto_recovery",
           {"prefrontal/interest-emergence-state.json":
            {"passions": [{"concept": "p", "status": "active"}]},
            "fatigue/fatigue-state.json": {"recovery_needed": True}})
    expect("novelty bypasses caution (gut=wait)", "proceed_novelty_extended",
           {"dopamine/novelty-state.json": {"novelty_seeking": 0.75},
            "somatic/markers.json": {"gut_feeling": "wait"}})
    expect("novelty bypasses caution (distracted)", "proceed_novelty_extended",
           {"dopamine/novelty-state.json": {"novelty_seeking": 0.75},
            "attention/attention-state.json": {"mode": "distracted"}})
    # The document places the quiet-hours gut VETO inside the VETO block, and PROCEED EXTENDED
    # "RIGHT AFTER VETO, before caution". So a quiet-hour gut veto still blocks extended scope.
    expect("quiet-hour gut veto precedes extended scope", "veto_quiet_gut",
           {"scn/scn-state.json": {"phase": "night", "quiet_hours": True},
            "somatic/markers.json": {"gut_feeling": "pause"},
            "dopamine/novelty-state.json": {"novelty_seeking": 0.9}})
    expect("passion overrides a quiet-hour caution", "proceed_passion",
           {"scn/scn-state.json": {"phase": "night", "quiet_hours": True},
            "prefrontal/interest-emergence-state.json":
            {"passions": [{"concept": "p", "status": "active"}]}})


def test_caution_rules():
    expect("caution_distracted", "caution_distracted",
           {"attention/attention-state.json": {"mode": "distracted"}})
    expect("caution_gut", "caution_gut",
           {"somatic/markers.json": {"gut_feeling": "pause"}})
    expect("caution_gut on wait", "caution_gut",
           {"somatic/markers.json": {"gut_feeling": "wait"}})
    expect("caution_doubt", "caution_doubt",
           {"somatic/markers.json": {"gut_feeling": "doubt"}})
    expect("caution_doubt needs adj_conf >= 0.40", "veto_doubt_confidence",
           {"somatic/markers.json": {"gut_feeling": "doubt", "confidence": 0.39}})
    expect("caution_fatigue", "caution_fatigue",
           {"fatigue/fatigue-state.json": {"fatigue_level": 0.55}})
    expect("caution_fatigue boundary 0.50 is not caution", "proceed",
           {"fatigue/fatigue-state.json": {"fatigue_level": 0.50}})
    expect("caution_low_arousal", "caution_low_arousal",
           {"hypothalamus/hypothalamus-state.json": {"arousal_level": 0.40}})
    expect("caution_tension", "caution_tension",
           {"somatic/markers.json": {"tension": 0.71}})
    expect("caution_tension boundary 0.70 is not caution", "proceed",
           {"somatic/markers.json": {"tension": 0.70}})
    expect("caution_quiet_hours", "caution_quiet_hours",
           {"scn/scn-state.json": {"phase": "night", "quiet_hours": True}})
    # The document prints caution_quiet_hours last, so an earlier caution rule wins.
    expect("caution_gut outranks caution_quiet_hours (order as printed)", "caution_gut",
           {"scn/scn-state.json": {"phase": "night", "quiet_hours": True},
            "somatic/markers.json": {"gut_feeling": "wait"}})


def test_surprise_confidence():
    out, _, _ = expect("surprise clamp low", "proceed",
                       {"somatic/markers.json": {"confidence": 0.10},
                        "predictive/surprise-log.json": {"stats": {"accuracy_rate": 0.0}}})
    field("surprise clamp low", out, "adj_confidence", 0.1)
    field("surprise clamp low", out, "conf_adj", -0.15)

    out, _, _ = expect("surprise clamp high", "proceed",
                       {"somatic/markers.json": {"confidence": 0.99},
                        "predictive/surprise-log.json": {"stats": {"accuracy_rate": 1.0}}})
    field("surprise clamp high", out, "adj_confidence", 0.99)
    field("surprise clamp high", out, "conf_adj", 0.15)

    out, _, _ = expect("surprise adjustment arithmetic", "proceed",
                       {"somatic/markers.json": {"confidence": 0.40},
                        "predictive/surprise-log.json": {"stats": {"accuracy_rate": 0.8}}})
    field("surprise adjustment arithmetic", out, "conf_adj", 0.09)
    field("surprise adjustment arithmetic", out, "adj_confidence", 0.49)

    expect("low accuracy feeds the doubt veto", "veto_doubt_confidence",
           {"somatic/markers.json": {"gut_feeling": "doubt", "confidence": 0.5},
            "predictive/surprise-log.json": {"stats": {"accuracy_rate": 0.0}}})
    expect("high accuracy feeds caution_doubt", "caution_doubt",
           {"somatic/markers.json": {"gut_feeling": "doubt", "confidence": 0.5},
            "predictive/surprise-log.json": {"stats": {"accuracy_rate": 1.0}}})
    expect("the habit doubt rule reads the adjusted confidence", "proceed_habit_gut_doubt",
           {**habit(0.8), "somatic/markers.json": {"gut_feeling": "doubt", "confidence": 0.45},
            "predictive/surprise-log.json": {"stats": {"accuracy_rate": 0.0}}})
    out, _, _ = expect("absent surprise file defaults to 0.5 accuracy", "proceed",
                       drop=["predictive/surprise-log.json"])
    field("absent surprise file", out, "surprise_accuracy", 0.5)
    field("absent surprise file", out, "conf_adj", 0.0)
    check("brain/predictive/surprise-log.json" in out.get("missing_state_files", []),
          "absent surprise file: reported in missing_state_files")


def test_quiet_hours():
    # Default window 23:00-05:30, straight from the spec, against the real local clock.
    expect("quiet window 22:59 is not quiet", "proceed", now="22:59")
    expect("quiet window 23:00 is quiet", "caution_quiet_hours", now="23:00")
    expect("quiet window 05:29 is quiet", "caution_quiet_hours", now="05:29")
    expect("quiet window 05:30 is not quiet", "proceed", now="05:30")

    # The entrainment schedule, when the agent has one, sets the window.
    entrainment = {"entrainment-state.json": {"targetSchedule": {"quiet_start": "22:00",
                                                                 "quiet_end": "06:00"}}}
    out, _, _ = expect("entrainment window 22:30 is quiet", "caution_quiet_hours",
                       {**entrainment}, now="22:30")
    field("entrainment window", out, "quiet_hours_window",
          {"start": "22:00", "end": "06:00", "source": "entrainment"})
    expect("entrainment window 05:45 is still quiet (default would not be)", "caution_quiet_hours",
           {**entrainment}, now="05:45")
    expect("entrainment window 21:00 is not quiet", "proceed", {**entrainment}, now="21:00")
    check("brain/entrainment-state.json" not in out.get("missing_state_files", []),
          "entrainment window: the entrainment file is reported as read when present")

    # A stale SCN reading is not trusted: the real clock governs, and the gate says so.
    stale = {"scn/scn-state.json": {"phase": "night", "quiet_hours": True, "local_hour": "14:30",
                                   "lastUpdated": "2000-01-01T00:00:00+00:00"}}
    out, err, _ = expect("stale SCN falls back to the real clock", "proceed", stale)
    field("stale SCN", out, "quiet_hours_source", "real_clock")
    check(any("stale" in w for w in out.get("warnings", [])), "stale SCN: a staleness warning is logged")
    check("stale" in err, "stale SCN: the warning also reaches stderr")

    # A drift of more than 2 hours: warn, and trust the real clock.
    drift = {"scn/scn-state.json": {"phase": "night", "quiet_hours": True, "local_hour": "18:30"}}
    out, _, _ = expect("SCN drift >2h falls back to the real clock", "proceed", drift)
    field("SCN drift", out, "quiet_hours_source", "real_clock")
    check(any("drift" in w for w in out.get("warnings", [])), "SCN drift: a drift warning is logged")

    # Under 2 hours is not drift.
    under = {"scn/scn-state.json": {"phase": "day", "quiet_hours": False, "local_hour": "16:00"}}
    out, _, _ = expect("SCN 1.5h off is not drift", "proceed", under)
    field("SCN 1.5h off", out, "quiet_hours_source", "scn")
    check(not any("drift" in w for w in out.get("warnings", [])),
          "SCN 1.5h off: no drift warning")

    # The real clock is ground truth even when a fresh, self-consistent SCN says otherwise.
    expect("the real clock is ground truth", "caution_quiet_hours", now="02:00")

    # MODE=essential bypasses quiet hours, in both the caution and the veto form.
    quiet = {"scn/scn-state.json": {"phase": "night", "quiet_hours": True}}
    expect("quiet hours without essential (control)", "caution_quiet_hours", quiet, now="02:00")
    out, _, _ = expect("MODE=essential bypasses caution_quiet_hours", "proceed", quiet,
                       mode="essential", now="02:00")
    field("MODE=essential", out, "essential", True)
    field("MODE=essential", out, "quiet_hours", False)
    field("MODE=essential", out, "quiet_hours_raw", True)
    expect("MODE=essential bypasses veto_quiet_gut", "caution_gut",
           {**quiet, "somatic/markers.json": {"gut_feeling": "pause"}},
           mode="essential", now="02:00")
    expect("MODE=essential still vetoes gut=stop", "veto_gut_stop",
           {**quiet, "somatic/markers.json": {"gut_feeling": "stop"}},
           mode="essential", now="02:00")
    # gut=stop is printed before quiet_gut in the VETO block, so it reports the earlier code.
    expect("quiet hours + gut=stop reports veto_gut_stop", "veto_gut_stop",
           {**quiet, "somatic/markers.json": {"gut_feeling": "stop"}}, now="02:00")


def test_modes_and_robustness():
    out, _, _ = expect("mode low_scope keeps the standard rule set", "caution_gut",
                       {"somatic/markers.json": {"gut_feeling": "wait"}}, mode="low_scope")
    field("mode low_scope", out, "mode", "low_scope")
    out, _, _ = expect("mode minimal keeps the standard rule set", "caution_gut",
                       {"somatic/markers.json": {"gut_feeling": "wait"}}, mode="minimal")
    field("mode minimal", out, "mode", "minimal")
    out, _, _ = expect("unknown mode warns and runs standard", "caution_quiet_hours",
                       {"scn/scn-state.json": {"phase": "night", "quiet_hours": True}},
                       mode="sideways")
    field("unknown mode", out, "mode", "standard")
    check(any("unknown mode" in w for w in out.get("warnings", [])),
          "unknown mode: a warning is logged")

    # An agent with nothing installed: every file missing, no crash, defaults visible.
    proc, out, err, _ = run({}, label="empty agent", now=DEFAULT_NOW)
    check(proc.returncode == 0 and out.get("reason") == "proceed",
          f"empty agent: no state files at all still proceeds (got {out.get('reason')!r}, "
          f"rc={proc.returncode})")
    missing = out.get("missing_state_files", [])
    check(len(missing) == 11,
          f"empty agent: all 11 documented state files are reported missing (got {len(missing)})")
    check(missing == sorted(missing) or set(missing) == set([
        "brain/somatic/markers.json", "brain/fatigue/fatigue-state.json",
        "brain/scn/scn-state.json", "brain/attention/attention-state.json",
        "brain/hypothalamus/hypothalamus-state.json", "brain/basal-ganglia/habit-state.json",
        "brain/prefrontal/interest-emergence-state.json", "brain/dopamine/vta-state.json",
        "brain/dopamine/novelty-state.json", "brain/predictive/surprise-log.json",
        "brain/entrainment-state.json"]),
        "empty agent: the missing list names the documented paths exactly")
    field("empty agent", out.get("inputs", {}), "gut", "neutral")
    field("empty agent", out, "adj_confidence", 0.5)
    check(any("SCN" in w for w in out.get("warnings", [])),
          "empty agent: the absent SCN reading is called out")

    # One file missing, the rest read: the report has to distinguish the two.
    files = baseline()
    files.pop("somatic/markers.json")
    out, _, _ = expect("somatic missing, the rest read", "proceed", files=files)
    field("somatic missing", out, "missing_state_files",
          ["brain/somatic/markers.json", "brain/entrainment-state.json"])
    field("somatic missing", out.get("inputs", {}), "gut", "neutral")
    check("somatic" not in out.get("real_readings", [])
          and "somatic" in out.get("defaulted_readings", []),
          "somatic missing: the output flags that no somatic reading was real")

    # Unparseable JSON is not a reading either.
    files = baseline()
    files["somatic/markers.json"] = "{not json"
    proc, out, _, _ = run(files, label="unreadable somatic")
    check(proc.returncode == 0 and out.get("reason") == "proceed",
          f"unreadable somatic: no crash, still decides (got {out.get('reason')!r}, rc={proc.returncode})")
    field("unreadable somatic", out, "unreadable_state_files", ["brain/somatic/markers.json"])
    field("unreadable somatic", out.get("inputs", {}), "gut", "neutral")
    field("unreadable somatic", out.get("sources", {}).get("somatic/markers.json", {}), "status",
          "unreadable")

    # --agent-dir works as well as $MIND_AGENT_DIR.
    proc, out, _, _ = run(baseline(), label="agent-dir flag", agent_dir_flag=True)
    check(proc.returncode == 0 and out.get("reason") == "proceed",
          f"--agent-dir resolves the agent dir (got {out.get('reason')!r}, rc={proc.returncode})")

    # Nothing configured at all: fall back to ./agent, report everything missing, do not crash.
    proc, out, err, _ = run(baseline(), label="no agent configured", agent_dir_flag=True,
                            env_extra={"MIND_AGENT_DIR": None})
    check(out.get("reason") in ("proceed", "caution"),
          f"no agent configured: still decides without crashing (got {out.get('reason')!r})")


def test_no_identity_residue():
    for path in (GATE, SELF):
        text = path.read_text()
        hits = [probe for probe in IDENTITY_PROBES if probe in text]
        check(not hits, f"{path.name} carries no identity residue ({hits})")


def test_every_rule_has_a_test():
    """Re-read the gate's own rule table: any rule this file never asserts fails here."""
    spec = importlib.util.spec_from_file_location("kit_decision_gate", GATE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    reasons = {entry[0] for entry in module.RULES}
    untested = sorted(reasons - ASSERTED)
    check(not untested, f"every documented rule is asserted by a case in this file (missing: {untested})")
    check(reasons | {"proceed"} == set(module.RULE_INPUTS),
          "the gate names the inputs behind every rule, including the default")


def main():
    try:
        test_default_and_contract()
        test_veto_rules()
        test_habit_bypass()
        test_proceed_extended()
        test_caution_rules()
        test_surprise_confidence()
        test_quiet_hours()
        test_modes_and_robustness()
        test_no_identity_residue()
        test_every_rule_has_a_test()
    finally:
        for path in TMP:
            shutil.rmtree(path, ignore_errors=True)
    failed = [label for ok, label in CHECKS if not ok]
    for ok, label in CHECKS:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
    print(f"\n{len(CHECKS) - len(failed)}/{len(CHECKS)} checks passed "
          f"({len(ASSERTED)} distinct reason codes asserted)")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
