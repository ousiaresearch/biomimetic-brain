# Biomimetic Decision Gate — Integration Status
**Updated:** 2026-03-26 07:45 AM EST | **Palantir**

---

## Signal Sources → Gate

| Signal | File | Metric | Gate Weight | Status |
|--------|------|--------|-------------|--------|
| Somatic (gut) | `brain/somatic/markers.json` | gut_feeling | PRIMARY | ✅ |
| Fatigue | `brain/fatigue/fatigue-state.json` | recovery_needed, fatigue_level | PRIMARY | ✅ |
| SCN (quiet hours) | `brain/scn/scn-state.json` | phase + real clock | PRIMARY | ✅ |
| Novelty | `brain/dopamine/novelty-state.json` | novelty_seeking | MODULATOR | ✅ |
| Surprise/Predictive | `brain/predictive/surprise-log.json` | accuracy_rate | MODULATOR | ✅ |
| Entrainment schedule | `brain/entrainment-state.json` | targetSchedule | CONSTANT | ✅ |

---

## Gate Logic (v4)

### VETO (exit 1) — Block all action
```
IF recovery_needed=true              → "veto_recovery"
IF fatigue > 0.70                   → "veto_fatigue"
IF hypothalamus arousal < 0.30       → "veto_low_arousal"
IF hypothalamus drive=recovery AND gut ∈ {pause,stop} → "veto_recovery_state"
IF gut=stop                         → "veto_gut_stop"
IF distracted AND gut=pause          → "veto_distracted_pause"
IF distracted AND gut=doubt AND adj_conf < 0.50 → "veto_distracted_doubt"
IF gut=pause AND energy < 0.35      → "veto_pause_energy"
IF gut=doubt AND adj_conf < 0.40    → "veto_doubt_confidence"
IF quiet_hours AND gut ∈ {pause,stop} → "veto_quiet_gut"
```

### BASAL GANGLIA HABIT BYPASS (before gut-based veto)
```
IF strong_habit (strength ≥ 0.7) AND gut=stop → PROCEED (habit override)
IF strong_habit AND gut=pause AND energy ≥ 0.20 → PROCEED (habit override)
IF strong_habit AND gut=doubt AND adj_conf ≥ 0.30 → PROCEED (habit override)
```

### PROCEED EXTENDED (exit 0) — Checked RIGHT AFTER VETO, before caution
```
IF active_passions > 0              → "proceed_passion" (HIGHEST PRIORITY)
IF active_convictions > 0           → "proceed_conviction"
IF emergent_interests > 0           → "proceed_curiosity_extended"
IF novelty > 0.7 AND vta > 0.7      → "proceed_extended_surge"
IF novelty > 0.7                     → "proceed_novelty_extended"
IF vta > 0.7                         → "proceed_vta_extended"
```

### CAUTION (exit 2) — Proceed with care
```
IF distracted AND gut=go_ahead        → "caution_distracted"
IF gut ∈ {pause, wait}              → "caution_gut"
IF gut=doubt AND adj_conf ≥ 0.40     → "caution_doubt"
IF fatigue > 0.50                   → "caution_fatigue"
IF hypothalamus arousal < 0.50      → "caution_low_arousal"
IF tension > 0.70                   → "caution_tension"
IF quiet_hours (non-essential)      → "caution_quiet_hours"
```
IF novelty_seeking > 0.70          → "proceed_novelty_extended" (bypass caution)
```

### Surprise Accuracy → Confidence Adjustment
```
surprise_accuracy (0.0-1.0) → conf_adj = (accuracy - 0.5) × 0.3
adj_confidence = clamp(confidence + conf_adj, 0.1, 0.99)
→ Low prediction accuracy reduces confidence signal (metacognitive loop)
```

### Quiet Hours — Real Clock Logic
```
Hours: 23:00-05:30 (from entrainment targetSchedule)
- Uses real local time (NY/EST) as ground truth
- Falls back to real clock when SCN phase is >2h stale
- Essential mode (MODE=essential) bypasses quiet hours
- Logs drift warnings when SCN contradicts real time
```

---

## Components

| File | Purpose |
|------|---------|
| `brain/somatic/scripts/marker-influence.py` | Gate logic v4 |
| `scripts/autonomous-cycle-gate.sh` | CLI wrapper, writes `brain/autonomy-scope.json` |
| `scripts/autonomous-queue.sh execute` | Gated queue task execution |
| `scripts/cron-agent-gate.sh` | Pre-spawn gate for cron agents |
| `scripts/cron-preamble.sh` | Bash source for cron prompts |
| `brain/autonomy-scope.json` | Scope state file (written by gate) |
| `brain/somatic/gut-feelings.json` | Decision log (30+ entries) |

---

## Cron Integration

### Gated Crons (biomimetic preamble added)
| Cron ID | Name | Gate Action |
|---------|------|-----------|
| `48955fe5-...` | palantir-moltx-engagement | VETO → skip silently |
| `c1eddfcf-...` | palantir-moltbook-engagement | VETO → skip silently |
| `65c53145-...` | palantir-pixel-art-vision | VETO → skip (leisure) |
| `9f4aca8b-...` | palantir-insight-capture | VETO → skip (low priority) |
| `c3b4e7ae-...` | palantir-rss-digest | VETO → skip (informational) |

**Pre-amble added to cron prompt:**
```
BEFORE STARTING: Read ~/.openclaw/workspace/brain/autonomy-scope.json. 
If scope="veto", reply "CRON_SKIP: biomimetic gate veto" and stop. 
Otherwise proceed.
```

### NOT Gated (essential infrastructure)
- `palantir-autonomous-thinking-loop` — IS the gate operator
- `palantir-somatic-monitor` — produces gut signals
- `palantir-fatigue-monitor` — produces fatigue signals
- `palantir-novelty-detector` — produces novelty signals
- `palantir-brain-maintenance` — health maintenance
- `palantir-morning-watch` — morning check-in
- `palantir-task-reminder` — task tracking

---

## Queue Integration

`autonomous-queue.sh execute`:
- Runs `autonomous-cycle-gate.sh` before picking task
- VETO → task deferred, not lost
- CAUTION → task runs with reduced scope
- PROCEED → normal execution

---

## Gap Status

| Gap | Status |
|-----|--------|
| Somatic + Fatigue → gate | ✅ DONE |
| SCN quiet hours → gate | ✅ DONE |
| Novelty → scope modulation | ✅ DONE |
| Surprise accuracy → confidence | ✅ DONE |
| Queue task execution gated | ✅ autonomous-queue.sh execute |
| Dream imagination bugs | ✅ Fixed |
| Cron pre-spawn (all deferrable) | ✅ 18/52 crons gated |
| **brain-state.json stale reads** | ✅ FIXED — surprise-analyzer + predictive-monitor now read per-system files |
| **brain-snapshot.sh rebuilt** | ✅ FIXED — now reads biomimetic state files |
| **Amy emotional decay system** | ✅ CREATED — brain/amy/emotional-decay-state.json + cron |
| **VTA drive state file** | ✅ CREATED — brain/dopamine/vta-state.json |
| **Decision gate v5** | ✅ VTA drive → extended scope modulation |

**Decision Gate v13 — Signal Sources (22):**
1. Somatic markers (gut/energy/confidence/tension/valence) ✅
2. Fatigue (recovery_needed, fatigue_level) ✅
3. SCN quiet hours (real clock 23:00-05:30) ✅
4. Novelty seeking (novelty_seeking) ✅
5. Surprise accuracy → metacognitive confidence ✅
6. VTA drive (current_drive from vta-state.json) ✅
7. Prefrontal curiosity (emergent interests) → extends scope, overrides gut-based caution ✅ **v7**
8. Prefrontal convictions + passions → hierarchical override ✅ **v8**
9. Attention mode (focused/distracted) → veto modulation ✅ **v10**
10. Hypothalamus arousal → VETO at <0.3, fatigue amplification at <0.5 ✅ **v10**
11. Basal Ganglia habits (strength>=0.7) → bypass gut-based vetoes ✅ **v10**
12. ACC uncertainty signal (>0.7) → VETO ✅ **v11**
13. ACC conflict level (>0.6 + non-go_ahead gut) → VETO ✅ **v11**
14. ACC moderate conflict/uncertainty → CAUTION ✅ **v11**
15. DMN self-discrepancy → VETO at >0.50, CAUTION at >0.30 ✅ **v12**
16. OFC prediction error → adjusts confidence (high error = reduced confidence) ✅ **v12**
17. NAc action urgency → modulates action threshold ✅ **v12**
18. ToM self-awareness → feeds into metacognitive confidence ✅ **v12**
19. Cerebellum procedural fluency → faster execution signal ✅ **v13**
20. LC arousal → VETO at DROWSY, CAUTION at <0.3 ✅ **v13**
21. Serotonin patience → CAUTION if impatient+doubt, VETO if agitated ✅ **v13**
22. Somatosensory battery → VETO at <0.20 ✅ **v13**
23. Somatosensory v2: API latency → health scoring ✅ **v14**
24. Somatosensory v2: expenditure level → energy depletion signal ✅ **v14**
25. A2A social nourishment → informational only (no loneliness signal) ✅ **v14**

**Integration: 100% complete**

---

*Decision gate integration complete. All signal producers left ungated (they produce the signals). All deferrable/creative/informational crons gated. Pattern: prepend biomimetic pre-amble to cron payload.message.*
