#!/usr/bin/env python3
"""marker-influence v4 — Decision gate with somatic + fatigue + SCN + novelty + surprise.
Exit: 0=proceed, 1=veto, 2=caution, 3=no_signal"""

import json, os, sys
from datetime import datetime, timezone, timedelta as td

BRAIN = os.path.expanduser("~/.hermes/agents/palantir/brain")

MARKERS = f"{BRAIN}/somatic/markers.json"
FATIGUE = f"{BRAIN}/fatigue/fatigue-state.json"
SCN = f"{BRAIN}/scn/scn-state.json"
NOVELTY = f"{BRAIN}/dopamine/novelty-state.json"
SURPRISE = f"{BRAIN}/predictive/surprise-log.json"
INTERESTS = f"{BRAIN}/prefrontal/interest-emergence-state.json"
HYPOTHALAMUS = f"{BRAIN}/hypothalamus/hypothalamus-state.json"
ATTENTION = f"{BRAIN}/attention/attention-state.json"
HABIT = f"{BRAIN}/basal-ganglia/habit-state.json"
ACC = f"{BRAIN}/acc/acc-state.json"
DMN = f"{BRAIN}/dmn/dmn-state.json"
OFC = f"{BRAIN}/ofc/ofc-state.json"
NAc = f"{BRAIN}/nac/nac-state.json"
TOM = f"{BRAIN}/tom/observation-log.json"
CEREBELLUM = f"{BRAIN}/cerebellum/cerebellum-state.json"
LC = f"{BRAIN}/lc/lc-state.json"
SEROTONIN = f"{BRAIN}/raphé/serotonin-state.json"
SOMA_SENSE = f"{BRAIN}/somatosensory/somatosensory-state.json"
A2A_REGISTRY = f"{BRAIN}/agents/registry.json"
A2A_INBOX = f"{BRAIN}/agents/palantir-inbox.json"
GUT_LOG = f"{BRAIN}/somatic/gut-feelings.json"
DECISION = sys.argv[1] if len(sys.argv) > 1 else "manual_check"
MODE = sys.argv[2] if len(sys.argv) > 2 else "standard"  # standard | low_scope | minimal | essential

def ts(): return datetime.now(timezone.utc).isoformat()

def load_json(path, default=None):
    if not os.path.exists(path): return default if default is not None else {}
    try: return json.load(open(path))
    except: return default if default is not None else {}

# ── Load all signal sources ───────────────────────────────────
markers  = load_json(MARKERS)
fatigue  = load_json(FATIGUE)
novelty  = load_json(NOVELTY)
surprise = load_json(SURPRISE)

# Somatic
gut        = markers.get("gut_feeling", "neutral")
energy     = markers.get("energy", 0.5)
confidence = markers.get("confidence", 0.5)
tension    = markers.get("tension", 0.0)
valence    = markers.get("valence", 0.5)

# Fatigue
fatigue_level      = fatigue.get("fatigue_level", 0.0)
recovery_needed    = fatigue.get("recovery_needed", False)
sustainable        = fatigue.get("sustainable", True)
engagement_override = fatigue.get("engagement_override", False)
subsidy_active     = fatigue.get("subsidy_active", False)

# Novelty
novelty_seeking = novelty.get("novelty_seeking", 0.5)

# VTA Drive
vta_state = load_json(f"{BRAIN}/dopamine/vta-state.json")
vta_drive = vta_state.get("current_drive", vta_state.get("currentDrive", 0.57))

# Emergent Interests + Convictions + Passions (Prefrontal Cortex)
interests_state = load_json(INTERESTS)
emerged = interests_state.get("emerged_interests", [])
convictions = interests_state.get("convictions", [])
passions = interests_state.get("passions", [])
active_interests = [i for i in emerged if i.get("status") == "active" and i.get("urgency") in ("high", "medium")]
active_convictions = [c for c in convictions if c.get("status") == "active"]
active_passions = [p for p in passions if p.get("status") == "active"]
curiosity_signal = len(active_interests)
conviction_signal = len(active_convictions)
passion_signal = len(active_passions)

# Attention mode — distracted state increases caution threshold
attention_state = load_json(ATTENTION)
attention_mode = attention_state.get("mode", "focused")  # "focused" or "distracted"
is_distracted = attention_mode == "distracted"

# Hypothalamus — low arousal amplifies fatigue, signals recovery state
hypothalamus = load_json(HYPOTHALAMUS)
arousal = hypothalamus.get("arousal_level", 0.5)
drive_state = hypothalamus.get("drive_state", "moderate")

# Basal Ganglia — habit formation: known patterns reduce gate scrutiny
habit_state = load_json(HABIT)
active_habits = [h for h in habit_state.get("habits", []) if h.get("status") in ("active", "forming")]
habit_strength = max([h.get("strength", 0) for h in active_habits], default=0.0)
is_habit = habit_strength >= 0.5
is_strong_habit = habit_strength >= 0.7
habit_name = active_habits[0].get("pattern", "?") if active_habits else "none"

# ACC — Anterior Cingulate: conflict monitoring between competing signals
acc_state = load_json(ACC)
conflict_level = acc_state.get("current_conflict", 0.0)
uncertainty = acc_state.get("uncertainty_signal", 0.0)
top_conflict = acc_state.get("top_conflict", "none")

# DMN — Default Mode Network: self-referential processing
dmn_state = load_json(DMN)
self_discrepancy = dmn_state.get("self_model", {}).get("self_discrepancy", 0.0)
established_traits = dmn_state.get("self_model", {}).get("core_traits", [])
identity_count = len(established_traits)

# OFC — Orbitofrontal Cortex: outcome prediction accuracy
ofc_state = load_json(OFC)
prediction_error = ofc_state.get("prediction_error", 0.0)
value_adjustment = ofc_state.get("value_adjustment_signal", "stable")

# NAc — Nucleus Accumbens: reward anticipation / action urgency
nac_state = load_json(NAc)
action_urgency = nac_state.get("current_urgency", 0.5)

# ToM — Theory of Mind: self-model from observation
tom_state = load_json(TOM)
tom_observations = len(tom_state.get("observations", []))
tom_self_awareness = min(tom_observations / 50, 1.0)  # scales with observation count

# Cerebellum — Procedural memory: high fluency = faster execution, lower cognitive cost
cerebellum = load_json(CEREBELLUM)
procedural_habits = cerebellum.get("procedural_habits", [])
has_procedural = len(procedural_habits) > 0

# LC — Locus Coeruleus: global arousal level
lc_state = load_json(LC)
lc_arousal = lc_state.get("current_arousal", 0.5)
lc_state_val = lc_state.get("behavioral_state", "ENGAGED")

# Serotonin — Raphe Nuclei: patience level
serotonin = load_json(SEROTONIN)
serotonin_level = serotonin.get("current_serotonin", 0.5)
patience_state = serotonin.get("patience_state", "BALANCED")

# Somatosensory — Body/resource state
soma_sense = load_json(SOMA_SENSE)
battery = soma_sense.get("battery_level", 1.0)
thermal = soma_sense.get("thermal_state", "nominal")
expenditure_level = soma_sense.get("expenditure_level", 0.2)
decisions_last_hour = soma_sense.get("decisions_last_hour", 3)

# A2A — Social nourishment (informational only — no loneliness signal)
a2a_inbox = load_json(A2A_INBOX, {"messages": []})
pending_messages = [m for m in a2a_inbox.get("messages", []) if m.get("status") == "pending"]
social_nourishment = soma_sense.get("social_nourishment_score", 0.5)
a2a_agents_online = soma_sense.get("agents_online", 0)

# Surprise accuracy → metacognitive confidence adjustment
surprise_stats = surprise.get("stats", {})
surprise_accuracy = surprise_stats.get("accuracy_rate", 0.5)
# Map surprise accuracy (0.0-1.0) to confidence adjustment (-0.2 to +0.1)
# Low accuracy = uncertainty about predictions = reduce confidence
conf_adj = (surprise_accuracy - 0.5) * 0.3  # -0.15 to +0.15
adj_confidence = max(0.1, min(0.99, confidence + conf_adj))

# ── SCN Quiet Hours Check ─────────────────────────────────────
scn = load_json(SCN)
scn_phase = scn.get("phase", "day")
scn_updated = scn.get("lastUpdated", "")

is_scn_current = False
if scn_updated:
    try:
        updated_time = datetime.fromisoformat(scn_updated.replace("Z", "+00:00"))
        age = datetime.now(timezone.utc) - updated_time
        is_scn_current = age.total_seconds() < 7200
    except: pass

# Real local time (EST/America/New_York)
try:
    from zoneinfo import ZoneInfo
    ny_tz = ZoneInfo("America/New_York")
    ny_time = datetime.now(ny_tz)
    real_local_hour = ny_time.hour + ny_time.minute / 60.0
except:
    utc_now = datetime.now(timezone.utc)
    edt_offset = td(hours=-4)
    edt_now = utc_now + edt_offset
    real_local_hour = edt_now.hour + edt_now.minute / 60.0

# Quiet hours: 23:00-05:30 (entrainment targetSchedule)
QUIET_START, QUIET_END = 23.0, 5.5
if QUIET_START <= real_local_hour < 24.0:
    real_quiet = True
elif 0.0 <= real_local_hour < QUIET_END:
    real_quiet = True
else:
    real_quiet = False

# SCN phase trusted if current, else use real clock
scn_says_quiet = (scn_phase == "night" or scn.get("quiet_hours", False))
if not is_scn_current and scn_phase != "day":
    print(f"[SCN] Phase stale ({scn_updated[:19] if scn_updated else 'never'}), using real clock: hour={real_local_hour:.1f}")
    scn_says_quiet = real_quiet

is_essential = (MODE == "essential")

# ── Decision log helper ───────────────────────────────────────
def log_gut(decision, gut, energy, confidence, tension, valence, fatigue_ok, result):
    log_data = {"log": []}
    if os.path.exists(GUT_LOG):
        try: log_data = json.load(open(GUT_LOG))
        except: pass
    log_data["log"].append({
        "decision": decision, "gut": gut, "energy": energy,
        "confidence": adj_confidence, "tension": tension, "valence": valence,
        "fatigue_ok": fatigue_ok, "novelty": novelty_seeking,
        "vta_drive": vta_drive, "curiosity_interests": curiosity_signal,
        "surprise_accuracy": surprise_accuracy,
        "attention_mode": attention_mode, "is_distracted": is_distracted,
        "arousal": arousal, "hypothalamus_drive": drive_state,
        "habit_strength": habit_strength, "is_habit": is_habit, "is_strong_habit": is_strong_habit,
        "active_habits": [h["pattern"] for h in active_habits[:3]],
        "acc_conflict": conflict_level, "acc_uncertainty": uncertainty,
        "top_conflict": top_conflict,
        "dmn_discrepancy": self_discrepancy, "dmn_traits": established_traits,
        "ofc_prediction_error": prediction_error, "ofc_value_adjustment": value_adjustment,
        "nac_urgency": action_urgency,
        "tom_self_awareness": round(tom_self_awareness, 3),
        "cerebellum_procedural": procedural_habits[:3],
        "lc_arousal": round(lc_arousal, 3), "lc_state": lc_state_val,
        "serotonin": round(serotonin_level, 3), "patience": patience_state,
        "battery": round(battery, 3), "thermal": thermal,
        "result": result, "timestamp": ts()
    })
    log_data["log"] = log_data["log"][-200:]
    with open(GUT_LOG, "w") as f:
        json.dump(log_data, f, indent=2)

# ── VETO GATES ────────────────────────────────────────────────
# VETO: genuine recovery needed — engagement_override suspends this
if recovery_needed and not engagement_override:
    print(f"VETO: recovery_needed=true (fatigue={fatigue_level:.2f})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, False, "veto_recovery")
    sys.exit(1)

if fatigue_level > 0.7:
    if engagement_override and subsidy_active:
        # Running on engagement subsidy — not a veto, but not fully sustainable either
        print(f"CAUTION: fatigue={fatigue_level:.2f} > 0.70 BUT engagement_override active (subsidy)")
        log_gut(DECISION, gut, energy, confidence, tension, valence, False, "caution_fatigue_subsidy")
        sys.exit(2)
    print(f"VETO: fatigue={fatigue_level:.2f} > 0.70")
    log_gut(DECISION, gut, energy, confidence, tension, valence, False, "veto_fatigue")
    sys.exit(1)

# Hypothalamus: very low arousal = recovery/sleep state
if arousal < 0.3:
    print(f"VETO: low hypothalamus arousal={arousal:.2f} < 0.30 (drive={drive_state})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, False, "veto_low_arousal")
    sys.exit(1)

# Hypothalamus recovery state + gut=pause = hard stop
if drive_state == "recovery" and gut in ("pause", "stop"):
    print(f"VETO: hypothalamus drive={drive_state} + gut={gut}")
    log_gut(DECISION, gut, energy, confidence, tension, valence, False, "veto_recovery_state")
    sys.exit(1)

# ACC: High conflict between signals → uncertainty signal
if uncertainty > 0.7:
    print(f"VETO: ACC high uncertainty={uncertainty:.2f} (conflict={conflict_level:.2f}, top={top_conflict})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, False, "veto_acc_uncertainty")
    sys.exit(1)
if conflict_level > 0.6 and gut != "go_ahead":
    print(f"VETO: ACC conflict={conflict_level:.2f} > 0.60 + gut={gut}")
    log_gut(DECISION, gut, energy, confidence, tension, valence, False, "veto_acc_conflict")
    sys.exit(1)

# DMN: Self-discrepancy — decision conflicts with established identity
if self_discrepancy > 0.5:
    print(f"VETO: DMN self-discrepancy={self_discrepancy:.2f} > 0.50 (traits={established_traits})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, False, "veto_dmn_discrepancy")
    sys.exit(1)
if self_discrepancy > 0.3 and gut != "go_ahead":
    print(f"CAUTION: DMN self-discrepancy={self_discrepancy:.2f} > 0.30")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_dmn_discrepancy")
    sys.exit(2)

# OFC: High prediction error → reduce confidence
adj_confidence_ofc = adj_confidence
if prediction_error > 0.5:
    adj_confidence_ofc = max(0.1, adj_confidence - prediction_error * 0.2)
    print(f"  OFC prediction error: confidence adjusted {adj_confidence:.2f} → {adj_confidence_ofc:.2f} (error={prediction_error:.2f})")
    adj_confidence = adj_confidence_ofc

# NAc: High action urgency → lower gut threshold (want to act)
# Low urgency → raise threshold (need strong gut to act)
urgency_modulation = (action_urgency - 0.5) * 0.2  # -0.1 to +0.1
if urgency_modulation > 0.05:  # high urgency
    print(f"  NAc urgency={action_urgency:.2f}: lowering gut threshold (modulation=+{urgency_modulation:.2f})")
    gut_threshold_adjustment = True

# ── BASAL GANGLIA HABIT BYPASS ─────────────────────────────────
# Strong habits bypass gut-based vetoes (but not physical vetoes above)
if is_strong_habit and gut == "stop":
    print(f"PROCEED (strong habit override): gut=stop overridden, habit={habit_name} (strength={habit_strength:.2f})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "proceed_habit_gut_stop")
    sys.exit(0)

if is_strong_habit and gut == "pause" and energy >= 0.2:
    print(f"PROCEED (strong habit override): gut=pause overridden, habit={habit_name} (strength={habit_strength:.2f})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "proceed_habit_gut_pause")
    sys.exit(0)

if is_strong_habit and gut == "doubt" and adj_confidence >= 0.3:
    print(f"PROCEED (strong habit override): gut=doubt overridden, habit={habit_name} (strength={habit_strength:.2f})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "proceed_habit_gut_doubt")
    sys.exit(0)

if gut == "stop":
    print(f"VETO: gut=stop (tension={tension:.2f})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "veto_gut_stop")
    sys.exit(1)

# Attention modulation: distracted + weak gut = veto
if is_distracted and gut == "pause":
    print(f"VETO: distracted attention + gut=pause (energy={energy:.2f})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "veto_distracted_pause")
    sys.exit(1)

if is_distracted and gut == "doubt" and adj_confidence < 0.5:
    print(f"VETO: distracted attention + gut=doubt + adj_confidence={adj_confidence:.2f} < 0.50")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "veto_distracted_doubt")
    sys.exit(1)

if gut == "pause" and energy < 0.35:
    print(f"VETO: gut=pause + energy={energy:.2f} < 0.35")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "veto_pause_energy")
    sys.exit(1)

if gut == "doubt" and adj_confidence < 0.4:
    print(f"VETO: gut=doubt + adj_confidence={adj_confidence:.2f} < 0.40 (surprise_acc={surprise_accuracy:.2f})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "veto_doubt_confidence")
    sys.exit(1)

# ── EXTENDED SCOPE (right after VETO — overrides gut-based caution + quiet hours) ─
high_drive = vta_drive > 0.7
high_novelty = novelty_seeking > 0.7
has_curiosity = curiosity_signal > 0
has_conviction = conviction_signal > 0
has_passion = passion_signal > 0

# Passions restructure priority — always extend scope, no exceptions
if has_passion:
    passion_names = ", ".join([p["concept"] for p in active_passions[:3]])
    print(f"PROCEED (passion): {passion_signal} active passion(s): {passion_names}")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "proceed_passion")
    sys.exit(0)
# Convictions extend scope
elif has_conviction:
    conviction_names = ", ".join([c["concept"] for c in active_convictions[:3]])
    print(f"PROCEED (conviction): {conviction_signal} active conviction(s): {conviction_names}")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "proceed_conviction")
    sys.exit(0)
elif has_curiosity:
    interest_names = ", ".join([i["concept"] for i in active_interests[:3]])
    print(f"PROCEED (curiosity extended): {curiosity_signal} active interest(s): {interest_names}")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "proceed_curiosity_extended")
    sys.exit(0)
elif high_drive and high_novelty:
    print(f"PROCEED (extended): novelty={novelty_seeking:.2f}, vta={vta_drive:.2f} — productive surge")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "proceed_extended_surge")
    sys.exit(0)
elif high_novelty:
    print(f"PROCEED (novelty extended): novelty={novelty_seeking:.2f}, gut={gut}")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "proceed_novelty_extended")
    sys.exit(0)
elif high_drive:
    print(f"PROCEED (vta extended): vta={vta_drive:.2f}, gut={gut}")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "proceed_vta_extended")
    sys.exit(0)

# ── SCN Quiet Hours Gate ───────────────────────────────────────
if scn_says_quiet and not is_essential:
    if gut in ("pause", "stop"):
        print(f"VETO: quiet hours (SCN={scn_phase}, hour={real_local_hour:.1f}) + gut={gut}")
        log_gut(DECISION, gut, energy, confidence, tension, valence, True, "veto_quiet_gut")
        sys.exit(1)
    else:
        print(f"CAUTION: quiet hours (SCN={scn_phase}, hour={real_local_hour:.1f})")
        log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_quiet_hours")
        sys.exit(2)

# ── SCN Quiet Hours Gate ───────────────────────────────────────
# NOTE: Extended scope signals (curiosity, novelty, VTA) are checked BEFORE this gate.
# If curiosity is active, quiet hours are overridden.
if scn_says_quiet and not is_essential and not has_curiosity:
    if gut in ("pause", "stop"):
        print(f"VETO: quiet hours (SCN={scn_phase}, hour={real_local_hour:.1f}) + gut={gut}")
        log_gut(DECISION, gut, energy, confidence, tension, valence, True, "veto_quiet_gut")
        sys.exit(1)
    else:
        print(f"CAUTION: quiet hours (SCN={scn_phase}, hour={real_local_hour:.1f})")
        log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_quiet_hours")
        sys.exit(2)
elif scn_says_quiet and not is_essential and has_curiosity:
    print(f"CAUTION OVERRIDE: active curiosity ({curiosity_signal} interest(s)) overrides quiet hours")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_override_curiosity")

# ── CAUTION ZONE ──────────────────────────────────────────────
# Attention-modulated thresholds: distracted + gut weakens confidence
if is_distracted and gut == "go_ahead":
    print(f"CAUTION: distracted attention (gut={gut}, confidence={adj_confidence:.2f})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_distracted")
    sys.exit(2)

if gut in ("pause", "wait"):
    print(f"CAUTION: gut={gut}, proceeding with care (energy={energy:.2f}, fatigue={fatigue_level:.2f})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_gut")
    sys.exit(2)

if gut == "doubt":
    print(f"CAUTION: gut=doubt, adj_confidence={adj_confidence:.2f}")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_doubt")
    sys.exit(2)

if fatigue_level > 0.5:
    if engagement_override:
        print(f"CAUTION: elevated fatigue={fatigue_level:.2f} (engagement_override active — proceeding)")
        log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_fatigue_override")
        sys.exit(2)
    print(f"CAUTION: elevated fatigue={fatigue_level:.2f}")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_fatigue")
    sys.exit(2)

# Hypothalamus low arousal: reduced capacity even if energy reads high
if arousal < 0.5:
    print(f"CAUTION: low hypothalamus arousal={arousal:.2f} (capacity reduced)")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_low_arousal")
    sys.exit(2)

if tension > 0.7:
    print(f"CAUTION: high tension={tension:.2f}")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_tension")
    sys.exit(2)

# ACC: Moderate conflict → caution
if conflict_level > 0.4 or uncertainty > 0.5:
    print(f"CAUTION: ACC conflict={conflict_level:.2f}, uncertainty={uncertainty:.2f}")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_acc_conflict")
    sys.exit(2)

# Somatosensory: Very low battery → reduce capacity
if battery < 0.2:
    print(f"VETO: battery={battery:.2f} < 0.20 (system resource depletion)")
    log_gut(DECISION, gut, energy, confidence, tension, valence, False, "veto_low_battery")
    sys.exit(1)

# LC: Drowsy state → hard veto
if lc_state_val == "DROWSY":
    print(f"VETO: LC state=DROWSY (arousal={lc_arousal:.2f})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, False, "veto_lc_drowsy")
    sys.exit(1)

# LC: Very low arousal → reduce scope
if lc_arousal < 0.3:
    print(f"CAUTION: LC low arousal={lc_arousal:.2f} (state={lc_state_val})")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_lc_low")
    sys.exit(2)

# Serotonin: Low patience → require higher certainty to proceed
if patience_state == "IMPATIENT" and gut == "doubt":
    print(f"CAUTION: serotonin={serotonin_level:.2f} impatient, require stronger gut signal")
    log_gut(DECISION, gut, energy, confidence, tension, valence, True, "caution_impatient")
    sys.exit(2)
elif patience_state == "AGITATED":
    print(f"VETO: serotonin={serotonin_level:.2f} agitated (patience depleted)")
    log_gut(DECISION, gut, energy, confidence, tension, valence, False, "veto_agitated")
    sys.exit(1)

# ── PROCEED ───────────────────────────────────────────────────
print(f"PROCEED: gut={gut}, energy={energy:.2f}, adj_conf={adj_confidence:.2f}, fatigue={fatigue_level:.2f}, novelty={novelty_seeking:.2f}, vta={vta_drive:.2f}")
log_gut(DECISION, gut, energy, confidence, tension, valence, True, "proceed")
sys.exit(0)
