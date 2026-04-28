#!/usr/bin/env python3
"""
fatigue-monitor.py — Track resource depletion with daytime engagement overrides.
Architecture: fatigue accumulates from cognitive load and low-valence signals.
Recovery can happen ANY time via strong engagement (novelty, drive, purpose).
This replaces the night-only recovery model with a full engagement/recovery balance.

Fatigue gates:
  - recovery_needed: fatigue > 0.7 OR high_tension+low_energy
  - sustainable: fatigue <= 0.7 AND NOT (late_night AND high_tension)
  - engagement_override: active when novelty OR VTA drive OR prefrontal interests are high
    → suspends fatigue accumulation from gut=doubt
    → allows sustainable daytime engagement even with elevated fatigue
"""

import json, os, sys
from datetime import datetime, timezone

BRAIN = os.path.expanduser("~/.hermes/agents/palantir/brain")
FTG = f"{BRAIN}/fatigue/fatigue-state.json"
BS  = f"{BRAIN}/brain-state.json"

def now_iso():
    return datetime.now(timezone.utc).isoformat()

def est_hour():
    return (datetime.now(timezone.utc).hour - 5) % 24

# ── Load state ────────────────────────────────────────────────────────────────
state = {
    "fatigue_level": 0.2,
    "cognitive_load": 0.3,
    "recovery_needed": False,
    "sustainable": True,
    "engagement_override": False,
    "override_reason": None,
}
if os.path.exists(FTG):
    try:
        state = json.load(open(FTG))
    except:
        pass

# ── Gather signals from all subsystems ────────────────────────────────────────
brain_systems = {}
if os.path.exists(BS):
    try:
        brain_systems = json.load(open(BS)).get("systems", {})
    except: pass

vta_d      = brain_systems.get("dopamine/VTA", {})
novelty_d  = brain_systems.get("novelty", {})
scn_d      = brain_systems.get("SCN", {})
hyp_d      = brain_systems.get("hypothalamus", {})
sm_d       = brain_systems.get("somatic", {})
pfc_d      = brain_systems.get("prefrontal", {})
nac_d      = brain_systems.get("nucleus-accumbens", {})

signals = {
    "vta_drive":              float(vta_d.get("drive", 0.5)),
    "novelty_seeking":         float(novelty_d.get("novelty", 0.5)),
    "novelty_boost":           float(novelty_d.get("vta_boost", 0.0)),
    "scn_phase":              scn_d.get("phase", "day"),
    "hypothalamus_arousal":    float(hyp_d.get("arousal", 0.3)),
    "energy":                 float(sm_d.get("energy", 0.5)),
    "gut_feeling":            sm_d.get("gut", "neutral"),
    "tension":                float(sm_d.get("tension", 0.0)),
    "valence":                float(sm_d.get("valence", 0.5)),
    "prefrontal_interests":   pfc_d.get("interests", 0),
    "nac_urgency":            float(nac_d.get("urgency", 0.0)),
    "hour":                   est_hour(),
}

# ── Engagement override ───────────────────────────────────────────────────────
# Like cognitive caffeine: high novelty or drive suspends doubt-driven fatigue.
# This is the daytime equivalent of nighttime recovery.
# Three pathways: novelty seeking, VTA drive, active prefrontal engagement.
OVERRIDE_THRESHOLDS = {
    "novelty":   0.65,   # novelty_seeking above this = engaged
    "vta_drive": 0.65,   # drive above this = flow state
    "interests": 3,      # active prefrontal interests above this = purposeful
    "nac_urgency": 0.5, # NAc urgency signals compelling goal pursuit
}

override_active = False
override_reasons = []

if signals["novelty_seeking"] >= OVERRIDE_THRESHOLDS["novelty"]:
    override_active = True
    override_reasons.append(f"novelty={signals['novelty_seeking']:.2f}")

if signals["vta_drive"] >= OVERRIDE_THRESHOLDS["vta_drive"]:
    override_active = True
    override_reasons.append(f"drive={signals['vta_drive']:.2f}")

if signals["prefrontal_interests"] >= OVERRIDE_THRESHOLDS["interests"]:
    override_active = True
    override_reasons.append(f"interests={signals['prefrontal_interests']}")

if signals["nac_urgency"] >= OVERRIDE_THRESHOLDS["nac_urgency"]:
    override_active = True
    override_reasons.append(f"nac_urgency={signals['nac_urgency']:.2f}")

state["engagement_override"] = override_active
state["override_reason"] = "; ".join(override_reasons) if override_reasons else None

# ── Fatigue computation ──────────────────────────────────────────────────────
prev_fatigue = state["fatigue_level"]

# Accumulation drivers (always active)
fatigue_increase = 0.0
if signals["tension"] > 0.5:
    fatigue_increase += 0.05
if signals["gut_feeling"] in ("stop",):
    fatigue_increase += 0.10
if signals["gut_feeling"] in ("doubt",) and not override_active:
    # Default: doubt costs fatigue. Override suspends this cost.
    fatigue_increase += 0.08
elif signals["gut_feeling"] in ("doubt",) and override_active:
    # Engaged AND doubting — reduced cost, but not zero (engagement isn't magic)
    fatigue_increase += 0.02
if signals["scn_phase"] in ("night",) and signals["hour"] >= 22:
    fatigue_increase += 0.04
if signals["hypothalamus_arousal"] > 0.6:
    fatigue_increase += 0.03

# Recovery drivers (engagement-aware)
fatigue_decrease = 0.0

# Nighttime physiological recovery (sleep cycle analog)
if signals["scn_phase"] in ("night", "pre-dawn") and signals["energy"] > 0.5:
    fatigue_decrease += 0.06

# Daytime engagement recovery: when deeply engaged, fatigue plateaus rather than climbs
if override_active and signals["gut_feeling"] not in ("stop",):
    # Engaged rest: plateau fatigue (no accumulation, no decrease either)
    fatigue_increase = 0.0
    fatigue_decrease += 0.01  # slow drift toward recovery even while engaged

# Deliberate rest signals
if signals["gut_feeling"] in ("pause", "neutral") and signals["energy"] < 0.4:
    fatigue_decrease += 0.08
if signals["hour"] >= 23 or signals["hour"] < 5:
    # Late-night biological window
    fatigue_decrease += 0.05

# Novelty boost as active recovery (engagement without obligation)
if signals["novelty_boost"] > 0.1:
    fatigue_decrease += signals["novelty_boost"] * 0.04

# Apply net change
net = fatigue_increase - fatigue_decrease
new_fatigue = max(0.0, min(1.0, state["fatigue_level"] + net))
state["fatigue_level"] = round(new_fatigue, 4)

# Cognitive load composite
state["cognitive_load"] = round(
    signals["hypothalamus_arousal"] * 0.4 +
    signals["tension"] * 0.4 +
    signals["energy"] * 0.2,
    4
)

# ── Sustainability gates ──────────────────────────────────────────────────────
hour = signals["hour"]
high_tension = signals["tension"] > 0.4
low_energy = signals["energy"] < 0.4
high_fatigue = state["fatigue_level"] > 0.7
cognitive_overload = state["cognitive_load"] > 0.5
late_night = hour >= 23 and signals["scn_phase"] in ("night", "evening")
engaged = override_active

# recovery_needed: genuine depletion requiring pause
state["recovery_needed"] = (
    high_fatigue and not engaged          # fatigued AND not sustaining via engagement
) or (
    high_tension and low_energy           # physically degraded
) or (
    cognitive_overload and not engaged    # overloaded AND not compensating
)

# sustainable: can continue without damage
state["sustainable"] = (
    not high_fatigue
) and not (
    late_night and high_tension
)

# Override note: if engaged but high_fatigue, recovery_needed=False but
# the system should know it's running on engagement subsidy
if engaged and high_fatigue:
    state["subsidy_active"] = True
    state["subsidy_reason"] = state["override_reason"]
else:
    state["subsidy_active"] = state.get("subsidy_active", False)
    state["subsidy_reason"] = None

# ── Recovery log ──────────────────────────────────────────────────────────────
recovery_log = state.get("recovery_log", [])
now = now_iso()

if state["recovery_needed"] and not state.get("last_recovery_warning"):
    recovery_log.append({
        "type": "recovery_needed",
        "fatigue": state["fatigue_level"],
        "signals": {k: v for k, v in signals.items() if k in (
            "energy", "gut_feeling", "tension", "vta_drive", "novelty_seeking"
        )},
        "timestamp": now,
        "override_active": override_active,
    })
    state["last_recovery_warning"] = now
    state["recovery_triggered"] = True
elif state["recovery_needed"] and state.get("recovery_triggered"):
    # Already warned, update signals
    pass
elif not state["recovery_needed"]:
    state["last_recovery_warning"] = None
    state["recovery_triggered"] = False

recovery_log = recovery_log[-50:]
state["recovery_log"] = recovery_log
state["last_updated"] = now
state["signals"] = signals

# ── Write ─────────────────────────────────────────────────────────────────────
with open(FTG, "w") as f:
    json.dump(state, f, indent=2)

# ── Output ────────────────────────────────────────────────────────────────────
flags = []
if override_active:  flags.append("OVERRIDE")
if state.get("subsidy_active"): flags.append("SUBSIDY")
if state["recovery_needed"]:    flags.append("RECOVERY_NEEDED")
if state["sustainable"]:       flags.append("SUSTAINABLE")

status_str = "|".join(flags) if flags else "OK"
print(f"Fatigue: level={state['fatigue_level']:.2f} | {status_str}")
print(f"  hour={hour:02d}h | phase={signals['scn_phase']} | gut={signals['gut_feeling']}")
print(f"  energy={signals['energy']:.2f} | tension={signals['tension']:.2f}")
print(f"  vta={signals['vta_drive']:.2f} | novelty={signals['novelty_seeking']:.2f} | interests={signals['prefrontal_interests']}")
print(f"  override={override_active} ({state.get('override_reason', 'none')})")
print(f"  net_delta={net:+.4f} (in={fatigue_increase:.3f} out={fatigue_decrease:.3f})")
if state.get("recovery_triggered"):
    print(f"  ⚠️  RECOVERY_NEEDED — sustainable={state['sustainable']}")
