#!/usr/bin/env python3
"""
generate-brain-state.py
Reads every subsystem state file under <agent-dir>/brain and writes the canonical
brain-state.json. This aggregate is the single source the decision gate and the
conversation-side kit read.

    MIND_AGENT_DIR=/path/to/agent python3 generate-brain-state.py

Called by brain-snapshot.sh on a schedule.
"""
import json, os, glob, sys
from datetime import datetime, timezone
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _agent_path import agent_dir

AGENT = agent_dir()
BRAIN = str(AGENT / "brain")
OUT   = str(AGENT / "brain-state.json")

def age_h(path: str) -> float:
    """Hours since file was last modified."""
    try:
        mtime = os.path.getmtime(path)
        return (datetime.now(timezone.utc) - datetime.fromtimestamp(mtime, tz=timezone.utc)).total_seconds() / 3600
    except:
        return 999.0

def last_updated_h(path: str) -> float:
    """Hours since the JSON's lastUpdated timestamp."""
    try:
        with open(path) as f:
            d = json.load(f)
        ts = d.get("lastUpdated") or d.get("lastUpdate") or d.get("_updated")
        if ts:
            dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
            return (datetime.now(timezone.utc) - dt).total_seconds() / 3600
    except:
        pass
    return age_h(path)

def status(age: float, max_age: float) -> str:
    if age <= max_age: return "active"
    return "stale"

def status_for(path, age: float, max_age: float) -> str:
    """Existence before age: an absent subsystem is ``missing``, never ``stale``.

    Only 7 of the 25 sites here used to test for file existence, so a file that was never installed —
    or was deleted — read as ``stale``, which the docs gloss as "gone quiet": present but quiet. A
    health summary whose reader cannot tell an absent subsystem from a silent one is not a gauge.
    """
    if not path or not os.path.exists(path):
        return "missing"
    return status(age, max_age)


def read_json(path: str):
    try:
        with open(path) as f:
            return json.load(f)
    except:
        return {}

def main():
    now = datetime.now(timezone.utc).isoformat()
    systems = {}

    # ── 1. Somatic / Insula ────────────────────────────────────────────────
    p = os.path.join(BRAIN, "somatic/markers.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["somatic"] = {
        "status": status_for(p, a, 8),
        "gut": d.get("gut_feeling", "unknown"),
        "energy": d.get("energy", 0),
        "valence": d.get("valence", 0.5),
        "confidence": d.get("confidence", 0),
        "tension": d.get("tension", 0),
        "age_h": round(a, 2),
        "max_age_h": 8,
        "critical": a > 24
    }

    # ── 2. Fatigue ─────────────────────────────────────────────────────────
    p = os.path.join(BRAIN, "fatigue/fatigue-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["fatigue"] = {
        "status": status_for(p, a, 24),
        "level": d.get("fatigue_level", 0),
        "recovery_needed": d.get("recovery_needed", False),
        "sustainable": d.get("sustainable", True),
        "engagement_override": d.get("engagement_override", False),
        "subsidy_active": d.get("subsidy_active", False),
        "override_reason": d.get("override_reason"),
        "age_h": round(a, 2),
        "max_age_h": 24,
        "critical": d.get("recovery_needed", False) and not d.get("engagement_override", False)
    }

    # ── 3. VTA (dopamine drive) ────────────────────────────────────────────
    p = os.path.join(BRAIN, "dopamine/vta-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["dopamine/VTA"] = {
        "status": status_for(p, a, 24),
        "drive": d.get("current_drive", d.get("currentDrive", 0.57)),
        "baseline": d.get("baseline_drive", 0.57),
        "threshold_high": d.get("threshold_high", 0.7),
        "threshold_low": d.get("threshold_low", 0.4),
        "novelty_boosts": d.get("novelty_boosts", 0),
        "age_h": round(a, 2),
        "max_age_h": 24,
        "critical": False
    }

    # ── 4. Novelty / NAc boost ─────────────────────────────────────────────
    p = os.path.join(BRAIN, "dopamine/novelty-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["novelty"] = {
        "status": status_for(p, a, 24),
        "novelty": d.get("novelty_seeking", 0.5),
        "vta_boost": d.get("vta_boost", 0),
        "age_h": round(a, 2),
        "max_age_h": 24,
        "critical": False
    }

    # ── 5. SCN (circadian) ─────────────────────────────────────────────────
    p = os.path.join(BRAIN, "scn/scn-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["SCN"] = {
        "status": status_for(p, a, 24),
        "phase": d.get("phase", "unknown"),
        "quiet_hours": d.get("quiet_hours", False),
        "local_hour": d.get("localHour", "?"),
        "age_h": round(a, 2),
        "max_age_h": 24,
        "critical": False
    }

    # ── 6. LC (locus coeruleus — norepinephrine) ───────────────────────────
    p = os.path.join(BRAIN, "lc/lc-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["LC"] = {
        "status": status_for(p, a, 24),
        "arousal": d.get("current_arousal", 0),
        "behavioral_state": d.get("behavioral_state", "unknown"),
        "age_h": round(a, 2),
        "max_age_h": 24,
        "critical": False
    }

    # ── 7. Amygdala ────────────────────────────────────────────────────────
    p = os.path.join(BRAIN, "amy/emotional-decay-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["amygdala"] = {
        "status": status_for(p, a, 24),
        "valence": d.get("valence", 0.5),
        "fear": d.get("fear", 0),
        "age_h": round(a, 2),
        "max_age_h": 24,
        "critical": d.get("fear", 0) > 0.7
    }

    # ── 8. Prefrontal Cortex ──────────────────────────────────────────────
    p = os.path.join(BRAIN, "prefrontal/interest-emergence-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    emerged = d.get("emerged_interests", [])
    convictions = d.get("convictions", [])
    passions = d.get("passions", [])
    systems["prefrontal"] = {
        "status": status_for(p, a, 48),
        "interests": len(emerged),
        "convictions": len(convictions),
        "passions": len(passions),
        "top_interest": emerged[0].get("concept","none") if emerged else "none",
        "top_conviction": convictions[0].get("concept","none") if convictions else "none",
        "age_h": round(a, 2),
        "max_age_h": 48,
        "critical": False
    }

    # ── 9. ACC (anterior cingulate cortex) ────────────────────────────────
    p = os.path.join(BRAIN, "acc/acc-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["ACC"] = {
        "status": status_for(p, a, 48),
        "conflict_detected": d.get("conflict_detected", False),
        "conflict_intensity": d.get("conflict_intensity", 0),
        "monitoring_active": d.get("monitoring_active", False),
        "age_h": round(a, 2),
        "max_age_h": 48,
        "critical": d.get("conflict_detected", False)
    }

    # ── 10. Basal Ganglia ─────────────────────────────────────────────────
    p = os.path.join(BRAIN, "basal-ganglia/habit-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["basal-ganglia"] = {
        "status": status_for(p, a, 168),
        "habits": len(d.get("habits", [])),
        "patterns": len(d.get("patterns", {})),
        "age_h": round(a, 2),
        "max_age_h": 168,
        "critical": False
    }

    # ── 11. Cerebellum ────────────────────────────────────────────────────
    p = os.path.join(BRAIN, "cerebellum/cerebellum-state.json")
    if not os.path.exists(p):
        p = os.path.join(BRAIN, "cerebellum-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["cerebellum"] = {
        "status": status_for(p, a, 168),
        "procedural": len(d.get("procedural_habits", [])),
        "age_h": round(a, 2),
        "max_age_h": 168,
        "critical": False
    }

    # ── 12. Hypothalamus ───────────────────────────────────────────────────
    p = os.path.join(BRAIN, "hypothalamus/hypothalamus-state.json")
    if not os.path.exists(p):
        p = os.path.join(BRAIN, "hypothalamus-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["hypothalamus"] = {
        "status": status_for(p, a, 24),
        "arousal": d.get("arousal_level", d.get("arousal", 0)),
        "homeostasis": d.get("homeostasis_offset", 0),
        "age_h": round(a, 2),
        "max_age_h": 24,
        "critical": False
    }

    # ── 13. Hippocampus ────────────────────────────────────────────────────
    p = os.path.join(BRAIN, "hippocampus/dream-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    stats = d.get("stats", {})
    systems["hippocampus"] = {
        "status": status_for(p, a, 48),
        "total_dreams": stats.get("total_dreams", 0),
        "videos_remaining_today": stats.get("videos_remaining_today", 0),
        "age_h": round(a, 2),
        "max_age_h": 48,
        "critical": False
    }

    # ── 14. Thalamus ───────────────────────────────────────────────────────
    p = os.path.join(BRAIN, "thalamus/thalamus-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["thalamus"] = {
        "status": status_for(p, a, 48),
        "relay_active": d.get("relay_active", False),
        "sensory_routing": d.get("sensory_routing", "unknown"),
        "age_h": round(a, 2) if os.path.exists(p) else 999,
        "max_age_h": 48,
        "critical": False
    }

    # ── 15. DMN (default mode network) ────────────────────────────────────
    p = os.path.join(BRAIN, "dmn/dmn-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    sm = d.get("self_model", {})
    systems["DMN"] = {
        "status": status_for(p, a, 48),
        "active": d.get("active", False),
        "self_narrative": d.get("self_narrative", "")[:120],
        "core_traits": sm.get("core_traits", [])[:5],
        "self_discrepancy": sm.get("self_discrepancy", "none"),
        "age_h": round(a, 2),
        "max_age_h": 48,
        "critical": False
    }

    # ── 16. OFC (orbitofrontal cortex) ───────────────────────────────────
    p = os.path.join(BRAIN, "ofc/ofc-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["OFC"] = {
        "status": status_for(p, a, 48),
        "reward_anticipation": d.get("reward_anticipation", 0),
        "outcome_accuracy": d.get("accuracy_by_domain", {}),
        "age_h": round(a, 2),
        "max_age_h": 48,
        "critical": False
    }

    # ── 17. NAc (nucleus accumbens) ────────────────────────────────────────
    p = os.path.join(BRAIN, "nac/nac-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["nucleus-accumbens"] = {
        "status": status_for(p, a, 24),
        "urgency": d.get("current_urgency", 0),
        "motivation_level": d.get("motivation_level", 0),
        "reward_anticipation": d.get("reward_anticipation", 0),
        "age_h": round(a, 2),
        "max_age_h": 24,
        "critical": d.get("current_urgency", 0) > 0.8
    }

    # ── 18. Somatosensory ─────────────────────────────────────────────────
    p = os.path.join(BRAIN, "somatosensory/somatosensory-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["somatosensory"] = {
        "status": status_for(p, a, 24),
        "battery": d.get("battery_level", "?"),
        "thermal": d.get("thermal_state", "?"),
        "age_h": round(a, 2) if os.path.exists(p) else 999,
        "max_age_h": 24,
        "critical": False
    }

    # ── 19. Values ─────────────────────────────────────────────────────────
    p = os.path.join(BRAIN, "values/values-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    vals = d.get("values", {})
    top = list(vals.keys())[0] if vals else "none"
    systems["values"] = {
        "status": status_for(p, a, 168),
        "top_value": top,
        "total_values": len(vals),
        "age_h": round(a, 2),
        "max_age_h": 168,
        "critical": False
    }

    # ── 20. Predictive Processing ────────────────────────────────────────
    p = os.path.join(BRAIN, "predictive/predictor-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    acc = d.get("stats", {}).get("accuracy_rate", None)
    if acc is None:
        ob = d.get("outcome_history", [])
        if ob:
            corr = sum(1 for o in ob if o.get("prediction_error", 1) == 0)
            acc = corr / len(ob) if ob else 0
        else:
            acc = 0
    systems["predictive"] = {
        "status": status_for(p, a, 48),
        "accuracy": round(acc, 3) if acc else 0,
        # Prefer the scored ledger's own count over the structural dict, which only holds
        # the temporal/contextual buckets and therefore always read as "2".
        "total_predictions": d.get("stats", {}).get("total_predictions",
                                                     len(d.get("predictions", {}))),
        "resolved_cases": d.get("stats", {}).get("matches", 0) + d.get("stats", {}).get("mismatches", 0),
        "unresolved": d.get("stats", {}).get("unresolved", 0),
        "unfalsifiable": d.get("stats", {}).get("unfalsifiable", 0),
        "resolution_rate": d.get("stats", {}).get("resolution_rate"),
        "brier_score": d.get("stats", {}).get("brier_score"),
        "age_h": round(a, 2),
        "max_age_h": 48,
        "critical": acc < 0.3
    }

    # ── 21. ToM (theory of mind / self-model) ────────────────────────────
    tom_path = os.path.join(BRAIN, "tom/observation-log.json")
    d = read_json(tom_path)
    a = last_updated_h(tom_path)
    systems["ToM"] = {
        "status": status_for(tom_path, a, 48),
        "observations": len(d.get("observations", [])),
        "self_model_updates": len(d.get("self_model_updates", [])),
        "age_h": round(a, 2) if os.path.exists(tom_path) else 999,
        "max_age_h": 48,
        "critical": False
    }

    # ── 22. Raphe Nuclei (serotonin) ──────────────────────────────────────
    for rp in [os.path.join(BRAIN, "raphé/serotonin-state.json"),
               os.path.join(BRAIN, "raphe/raphe-state.json")]:
        if os.path.exists(rp):
            p = rp
            break
    else:
        p = None
    d = read_json(p) if p and os.path.exists(p) else {}
    a = last_updated_h(p) if p and os.path.exists(p) else 999
    systems["raphe-nuclei"] = {
        "status": status_for(p, a, 48),
        "serotonin": d.get("current_serotonin", d.get("level", "?")),
        "patience": d.get("patience_state", "?"),
        "age_h": round(a, 2),
        "max_age_h": 48,
        "critical": False
    }

    # ── 23. Visual Cortex (dream imagery memory) ─────────────────────────
    p = os.path.join(BRAIN, "visual/visual-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    scenes = d.get("scenes", {})
    systems["visual-cortex"] = {
        "status": status_for(p, a, 168),
        "scene_count": len(scenes),
        "scenes": list(scenes.keys()),
        "age_h": round(a, 2) if os.path.exists(p) else 999,
        "max_age_h": 168,
        "critical": False
    }

    # ── 24. Habenula (anti-reward / disappointment) ──────────────────────
    p = os.path.join(BRAIN, "habenula/habenula-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["habenula"] = {
        "status": status_for(p, a, 168),
        "tonic_suppression": d.get("tonic_suppression", "?"),
        "recent_losses": len(d.get("recent_losses", [])),
        "age_h": round(a, 2) if os.path.exists(p) else 999,
        "max_age_h": 168,
        "critical": False
    }

    # ── 25. Reticular Formation (wake/sleep threshold) ───────────────────
    p = os.path.join(BRAIN, "reticular/reticular-state.json")
    d = read_json(p)
    a = last_updated_h(p)
    systems["reticular-formation"] = {
        "status": status_for(p, a, 24),
        "state": d.get("state", "?"),
        "arousal_threshold": d.get("arousal_threshold", "?"),
        "age_h": round(a, 2) if os.path.exists(p) else 999,
        "max_age_h": 24,
        "critical": False
    }

    # ── Summary ───────────────────────────────────────────────────────────
    healthy = sum(1 for s in systems.values() if s["status"] == "active")
    stale   = sum(1 for s in systems.values() if s["status"] == "stale")
    missing = sum(1 for s in systems.values() if s["status"] == "missing")
    critical = any(s.get("critical", False) for s in systems.values())

    result = {
        "timestamp": now,
                "generated_by": "generate-brain-state.py — reads all 25 subsystem files",
        "health_summary": {
            "score": f"{round(healthy/len(systems)*100)}%",
            "healthy": healthy,
            "stale": stale,
            "missing": missing,
            "critical": critical,
            "total": len(systems)
        },
        "systems": systems
    }

    with open(OUT, "w") as f:
        json.dump(result, f, indent=2)

    print(f"✅ brain-state.json written: {healthy}/{len(systems)} healthy, {stale} stale, {missing} missing")

if __name__ == "__main__":
    main()
