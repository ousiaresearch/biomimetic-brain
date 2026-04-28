#!/usr/bin/env python3
"""Somatic marker monitor — aggregates brain state → gut feeling."""

import json, os, sys
from datetime import datetime, timezone

BRAIN = os.path.expanduser("~/.hermes/agents/palantir/brain")
STATE = f"{BRAIN}/somatic/markers.json"
GUT_LOG = f"{BRAIN}/somatic/gut-feelings.json"
BS = f"{BRAIN}/brain-state.json"

def read_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

# Read from canonical brain-state.json systems
brain_systems = {}
if os.path.exists(BS):
    try:
        brain_systems = read_json(BS).get("systems", {})
    except: pass

vta_d  = brain_systems.get("dopamine/VTA", {})
amy_d  = brain_systems.get("amygdala", {})
ins_d  = brain_systems.get("somatic", {})
scn_d  = brain_systems.get("SCN", {})
hyp_d  = brain_systems.get("hypothalamus", {})

vta      = float(vta_d.get("drive", 0.5))
amy_v    = float(amy_d.get("valence", 0.5))
amy_a    = float(amy_d.get("arousal", 0.3))
insula_e = float(ins_d.get("energy", 0.5))  # insula engagement approximated by somatic energy
phase    = scn_d.get("phase", "evening")
hyp_a    = float(hyp_d.get("arousal", 0.3))

# Read previous somatic state for gut transition log
prev_gut = "neutral"
prev_conf = 0.5
if os.path.exists(STATE):
    try:
        s = read_json(STATE)
        prev_gut = s.get("gut_feeling", "neutral")
        prev_conf = s.get("confidence", 0.5)
    except: pass

# Composite signals
energy   = min(1.0, vta * insula_e + 0.1)
valence  = amy_v
arousal  = min(1.0, (amy_a + hyp_a) / 2 + 0.2)
tension  = max(0.0, min(1.0, abs(vta - insula_e)))
confidence = max(0.1, min(0.95, 1.0 - tension * 0.6 + 0.2))

# Gut feeling map
# Priority: danger > depletion > disengagement > valence
if tension > 0.7:   gut = "stop"
elif tension > 0.4:  gut = "wait"
elif energy < 0.35:  gut = "pause"       # resource depletion — most urgent
elif valence < 0.35: gut = "doubt"       # negative tone
elif insula_e < 0.3: gut = "neutral"      # disengaged but not depleted
elif valence > 0.7 and energy > 0.65: gut = "go_ahead"
elif prev_gut in ("pause","wait") and phase in ("evening","night"): gut = "pause"
else:                gut = "neutral"

# Write state
result = {
    "energy": round(energy, 3),
    "gut_feeling": gut,
    "valence": round(valence, 3),
    "arousal": round(arousal, 3),
    "confidence": round(confidence, 3),
    "tension": round(tension, 3),
    "decision_weights": {
        "gut_override": round(0.3 + tension * 0.3, 3),
        "logic_weight": round(0.7 - tension * 0.3, 3)
    },
    "last_updated": datetime.now(timezone.utc).isoformat(),
    "phase_signal": phase
}

with open(STATE, "w") as f:
    json.dump(result, f, indent=2)

# Log transition
if gut != prev_gut:
    log_data = {"log": []}
    if os.path.exists(GUT_LOG):
        try: log_data = json.load(open(GUT_LOG))
        except: pass
    log_data["log"].append({
        "from": prev_gut, "to": gut, "energy": round(energy,3),
        "valence": round(valence,3), "tension": round(tension,3),
        "confidence_before": prev_conf, "phase": phase,
        "timestamp": datetime.now(timezone.utc).isoformat()
    })
    log_data["log"] = log_data["log"][-100:]
    with open(GUT_LOG, "w") as f:
        json.dump(log_data, f, indent=2)
    print(f"Gut transition: {prev_gut} → {gut}", file=sys.stderr)

print(f"Somatic: gut={gut} | energy={energy:.3f} | tension={tension:.3f} | confidence={confidence:.3f}")
