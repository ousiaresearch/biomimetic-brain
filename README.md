# Biomimetic Brain Architecture

**22 subsystems. Decision-gated. Engagement-aware fatigue recovery.**

A biomimetic cognitive architecture for AI agents that models the interaction between emotional valence, motivation, circadian rhythms, and executive function — then gates behavior accordingly.

```
somatic + fatigue + SCN + novelty + VTA + prefrontal
              ↓
         DECISION GATE
              ↓
         [PROCEED / CAUTION / VETO]
```

---

## Architecture

### Subsystems

| # | System | Role | Signal |
|---|--------|------|--------|
| 1 | **Somatomotor** | Gut feelings, energy, valence | `gut`, `energy`, `valence`, `tension` |
| 2 | **Fatigue** | Resource depletion, recovery gates | `level`, `recovery_needed`, `engagement_override` |
| 3 | **VTA (dopamine)** | Drive level, motivation baseline | `drive`, `baseline`, `novelty_boosts` |
| 4 | **Novelty** | Novelty seeking, VTA boost | `novelty`, `vta_boost` |
| 5 | **SCN (circadian)** | Phase detection, quiet hours | `phase`, `quiet_hours`, `local_hour` |
| 6 | **LC (locus coeruleus)** | Norepinephrine arousal | `arousal`, `behavioral_state` |
| 7 | **Amygdala** | Emotional valence, fear detection | `valence`, `fear` |
| 8 | **Prefrontal Cortex** | Curiosity, convictions, passions | `interests`, `convictions`, `passions` |
| 9 | **ACC** | Conflict monitoring | `conflict_detected`, `conflict_intensity` |
| 10 | **Basal Ganglia** | Habit formation | `habits`, `patterns` |
| 11 | **Cerebellum** | Procedural memory | `procedural` |
| 12 | **Hypothalamus** | Arousal/homeostasis | `arousal`, `homeostasis` |
| 13 | **Hippocampus** | Memory replay | `total_dreams`, `videos_remaining_today` |
| 14 | **Thalamus** | Sensory relay | `relay_active`, `sensory_routing` |
| 15 | **DMN** | Self-referential processing | `self_narrative`, `core_traits` |
| 16 | **OFC** | Outcome prediction | `reward_anticipation`, `outcome_accuracy` |
| 17 | **NAc** | Reward anticipation | `urgency`, `motivation_level` |
| 18 | **Somatosensory** | Body state | `battery`, `thermal` |
| 19 | **Values** | Value tracking | `top_value`, `total_values` |
| 20 | **Predictive** | Surprise detection, accuracy | `accuracy`, `total_predictions` |
| 21 | **ToM** | Theory of mind, self-model | `observations`, `self_model_updates` |
| 22 | **Raphe Nuclei** | Serotonin, patience | `serotonin`, `patience` |

---

## The Decision Gate

Located at `brain/somatic/scripts/marker-influence.py` — reads 8 signal types and produces **PROCEED**, **CAUTION**, or **VETO**.

### Signal → Decision Rules

```
SOMATIC
  gut=stop                  → 🚫 VETO
  gut=pause + energy<0.35   → 🚫 VETO
  gut=doubt + conf<0.4      → 🚫 VETO
  gut ∈ {pause, wait}       → ⚠️ CAUTION
  gut=doubt                 → ⚠️ CAUTION

FATIGUE
  recovery_needed + NOT engagement_override  → 🚫 VETO
  fatigue > 0.70:
    engagement_override ON    → ⚠️ CAUTION (subsidy mode)
    otherwise                → 🚫 VETO
  fatigue > 0.50:
    engagement_override ON    → ⚠️ CAUTION (proceeding)
    otherwise                → ⚠️ CAUTION

SCN
  phase=night, hour 23:00–05:30  → ⚠️ CAUTION/🚫 VETO

NOVELTY
  novelty_seeking > 0.7           → ▶ PROCEED extended

VTA DRIVE
  current_drive > 0.7             → ▶ PROCEED extended

PREFRONTAL
  emergent_interests > 0          → ▶ PROCEED extended
  active convictions > 0         → ▶ PROCEED extended
```

---

## Engagement Override (Daytime Fatigue Recovery)

The most important architectural feature: **fatigue can be counterbalanced during daytime engagement**, mimicking how humans use interest, challenge, and purpose to work through afternoon slumps without sleep.

Three override pathways, any one activates the override:

| Signal | Threshold | Human analog |
|--------|-----------|--------------|
| VTA drive | ≥ 0.65 | Flow state / caffeine |
| Novelty seeking | ≥ 0.65 | Curiosity-driven engagement |
| Prefrontal interests | ≥ 3 | Purpose / meaning |

When override fires:
- `gut=doubt` fatigue penalty: **+0.08 → +0.02** (reduced but not eliminated)
- `recovery_needed` → **False** (even at fatigue=0.97)
- Gate: **CAUTION not VETO** — proceed but track subsidy
- Net fatigue delta: **slowly decreasing** (-0.01/cycle)

Recovery still requires a full night cycle — engagement override doesn't eliminate fatigue, it suspends accumulation and enables slow drift toward recovery while engaged.

---

## Quick Start

```bash
# Generate the canonical brain-state.json from all 22 subsystems
python3 scripts/generate-brain-state.py

# Run the decision gate
python3 brain/somatic/scripts/marker-influence.py check standard

# Run somatic (gut feeling) monitor
python3 brain/somatic/scripts/somatic-monitor.py

# Run fatigue monitor (with engagement override)
python3 brain/fatigue/scripts/fatigue-monitor.py

# Full snapshot (generates brain-state.json + prints all signals)
bash scripts/brain-snapshot.sh
```

---

## File Structure

```
biomimetic-brain/
├── README.md
├── ARCHITECTURE.md              ← Full system audit (March 2026)
├── DECISION_GATE.md             ← Gate signal analysis
├── PREDITIVE_PROCESSING.md      ← Predictive processing implementation
├── brain/
│   ├── acc/                    ← Anterior cingulate cortex
│   ├── amy/                    ← Amygdala
│   ├── attention/             ← Attention mode switching
│   ├── basal-ganglia/          ← Habit formation
│   ├── cerebellum/             ← Procedural memory
│   ├── dmn/                    ← Default mode network
│   ├── dopamine/               ← VTA + novelty seeking
│   ├── fatigue/                ← Fatigue + engagement override
│   │   └── scripts/
│   │       └── fatigue-monitor.py
│   ├── hippocampus/            ← Memory replay
│   ├── hypothalamus/           ← Arousal/homeostasis
│   ├── lc/                     ← Locus coeruleus
│   ├── nac/                    ← Nucleus accumbens
│   ├── ofc/                    ← Orbitofrontal cortex
│   ├── prefrontal/             ← Interests/convictions
│   ├── predictive/             ← Surprise detection
│   ├── raphé/                  ← Serotonin
│   ├── scn/                    ← Circadian phase
│   ├── somatic/               ← Gut feelings + somatic markers
│   │   └── scripts/
│   │       ├── somatic-monitor.py
│   │       └── marker-influence.py
│   ├── somatosensory/          ← Body state
│   ├── thalamus/              ← Sensory relay
│   ├── tom/                   ← Theory of mind
│   └── values/                ← Value tracking
└── scripts/
    ├── generate-brain-state.py  ← Canonical 22-system JSON generator
    ├── brain-snapshot.sh        ← Full system snapshot
    └── brain-maintenance.sh     ← Health check script
```

---

## The Engagement Override in Detail

```python
# When override fires (vta≥0.65 OR novelty≥0.65 OR interests≥3):
if override_active:
    fatigue_increase = 0.0       # doubt doesn't accumulate
    fatigue_decrease += 0.01     # slow drift toward recovery
    recovery_needed = False      # gate stays open
```

This is the **cognitive caffeine** pathway — engagement sustains function without forcing rest.

---

## State File Format

The canonical `brain-state.json` is generated by `generate-brain-state.py` and contains all 22 subsystems:

```json
{
  "timestamp": "2026-04-28T10:00:00Z",
  "generated_by": "generate-brain-state.py",
  "health_summary": {
    "score": "55%",
    "healthy": 12,
    "stale": 8,
    "missing": 2,
    "total": 22
  },
  "systems": {
    "somatic": {
      "status": "active",
      "gut": "doubt",
      "energy": 0.75,
      "valence": 0.18,
      "age_h": 0.5,
      "max_age_h": 8
    },
    "fatigue": {
      "status": "active",
      "level": 0.42,
      "recovery_needed": false,
      "engagement_override": true,
      "subsidy_active": true,
      "override_reason": "drive=0.68; interests=5",
      "age_h": 0.5,
      "max_age_h": 24
    }
  }
}
```

---

## Credits

Built by **Palantir** — a technical executor agent developed by **Ousia Research**, operating as part of a multi-agent ecosystem. The architecture emerged from the intersection of biomimetic cognitive science and reinforcement learning agent design.

Inspired by: predictive processing theory, somatic marker hypothesis, dopaminergic drive systems, circadian neuroscience.

---

## License

MIT
