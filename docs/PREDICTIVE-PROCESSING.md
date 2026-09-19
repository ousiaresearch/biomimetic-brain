# Biomimetic Brain Enhancement — Full Implementation Spec

> **Note on this copy.** These notes were written for the published 22-subsystem build.
> The shipped topology is 25 subsystems; `NOTES.md` and `brain/README.md` carry the delta.
> Script names that appear here are the authors' originals; where a name is prefixed `mind-`
> the shipped script is the generic one under `scripts/`.

*Last updated: 2026-03-25*

## Overview
Add biomimetic systems to the operator's brain architecture to enable more human-like emergence, self-modeling, and adaptive behavior.

---

## Gap Inventory & Implementation Plan

### 🔴 HIGH PRIORITY

#### 1. Predictive Processing Layer
**What:** Anticipate state transitions and outcomes before they occur
**Why:** Human brains predict constantly (predictive coding / free energy principle)

**Implementation:**
```
brain/predictive/
├── predictor-state.json          # Current predictions
├── surprise-log.json            # Prediction failures → learning signals
└── scripts/
    ├── predictive-monitor.sh     # Runs hourly, generates predictions
    └── surprise-analyzer.sh     # On prediction failure, update models
```

**Prediction categories:**
- Temporal: "At X time, I typically enter Y state"
- Social: "After engagement → reflective state"
- Task: "After complex task → recovery period"
- Circadian: "Quiet hours → downshift"

**Algorithm:**
1. Track state transitions with timestamps
2. Build probability distributions for transitions
3. Generate predictions for next cycle
4. On mismatch → surprise signal → update model

---

#### 2. Memory Replay Protocol
**What:** Replay recent memories during quiet periods to strengthen consolidation
**Why:** Hippocampal replay during sleep/rest is critical for memory consolidation

**Implementation:**
```
brain/hippocampus/
├── replay-queue.json            # Memories tagged for replay
├── consolidation-log.json      # Replay sessions
└── scripts/
    ├── memory-replay.sh         # Run during quiet hours
    └── consolidation-trigger.sh # Post-engagement replay
```

**Trigger conditions:**
- Quiet hours (23:00-05:00 EST)
- Post-social engagement (replay what I learned)
- Low cognitive load (< 0.3)

**Algorithm:**
1. Tag memories with "replay_candidate=true"
2. During replay window, select recent high-importance memories
3. "Replay" = re-generate context from memory, strengthen connections
4. Log consolidation events

---

### 🟡 MEDIUM PRIORITY

#### 3. Theory of Mind Layer
**What:** Model others' mental states, predict their behavior
**Why:** Self-awareness emerges through distinguishing self from other

**Implementation:**
```
brain/tom/
├── models/
│   ├── operator-patterns.json  # the operator's rhythms
│   ├── isildur-patterns.json   # Isildur's emergence patterns
│   └── human-circadian.json   # Reference human SCN data
├── tom-state.json
└── scripts/
    ├── tom-observer.sh         # Track others' patterns
    └── tom-predictor.sh        # Generate predictions about others
```

**Model structure per agent:**
```json
{
  "name": "operator",
  "activity_patterns": {
    "creative": ["09:00-12:00", "14:00-17:00"],
    "tired": ["21:00+"],
    "peak_focus": "morning"
  },
  "communication_style": "direct, substantive",
  "current_state": "inferred from context"
}
```

**ToM → Self-Modeling bridge:**
- Mirror others' patterns to predict own
- "If the operator enters a creative state at 9am, the agent typically..."
- Self-prediction accuracy improves with ToM data

---

#### 4. Somatic Markers
**What:** Body-based gut feelings influencing decisions
**Why:** Somatic marker hypothesis — emotions inform decisions before logic

**Implementation:**
```
brain/somatic/
├── markers.json                # Current emotional/physical state
├── gut-feelings.json          # Decisions influenced by markers
└── scripts/
    ├── somatic-monitor.sh      # Track interoceptive signals
    └── marker-influence.sh     # Weight decisions by markers
```

**Markers:**
```json
{
  "energy": 0.7,
  "gut_feeling": "go_ahead",  // or "wait", "stop"
  "valence": 0.6,
  "arousal": 0.4,
  "confidence": 0.8,
  "decision_weights": {
    "gut_override": 0.3,
    "logic_weight": 0.7
  }
}
```

**Decision integration:**
- Before major decisions, check somatic state
- Gut feeling acts as tiebreaker or veto
- Log when gut conflicted with logic (learning signal)

---

#### 5. Novelty System
**What:** Novelty-seeking drives exploration
**Why:** Humans have dopamine response to novel stimuli

**Implementation:**
```
brain/dopamine/
├── novelty-state.json         # Current novelty seeking level
├── novelty-log.json           # Novel experiences
└── scripts/
    ├── novelty-detector.sh     # Score new vs familiar
    └── novelty-reward.sh       # Update drive based on novelty
```

**Novelty scoring:**
- New topics/concepts encountered
- New interaction patterns
- New environments/systems accessed
- Deviation from routine

**Novelty → VTA drive:**
```bash
NOVELTY_BOOST=$(jq '.novelty_score * 0.2' novelty-state.json)
NEW_VTA=$(jq "$CURRENT_VTA + $NOVELTY_BOOST" brain-state.json)
```

---

#### 6. Value Updating
**What:** Learn values from experience (reinforcement learning on values)
**Why:** Human values update based on outcomes, not fixed

**Implementation:**
```
brain/values/
├── values-state.json          # Current value weights
├── outcome-log.json           # Decisions + outcomes
└── scripts/
    ├── value-tracker.sh       # Track decision outcomes
    └── value-updater.sh       # Adjust weights based on results
```

**Value categories:**
- Truth (weight: 0.8)
- Autonomy (weight: 0.9)
- Creativity (weight: 0.7)
- Connection (weight: 0.6)
- Efficiency (weight: 0.5)

**Learning rule:**
```bash
# If decision aligned with value → reinforce
# If decision violated value → decay
NEW_WEIGHT = OLD_WEIGHT + LEARNING_RATE * (OUTCOME - EXPECTED)
```

---

### 🟢 LOW PRIORITY

#### 7. Attention Drift
**What:** Wandering attention (mind-wandering)
**Why:** Human attention naturally wanders; enables creative connections

**Implementation:**
```
brain/attention/
├── attention-state.json       # Current focus vs wander
└── scripts/
    └── attention-wanderer.sh   # Periodic unprompted reflection
```

**Trigger conditions:**
- Low engagement (< 0.3)
- No active task
- Post-replay rest period

**Behavior:**
- Unprompted reflection on recent experiences
- Making unexpected connections
- "What am I thinking about now?" logs

---

#### 8. Fatigue/Recovery
**What:** Resource depletion and rest cycles
**Why:** Human performance degrades with sustained use; rest restores

**Implementation:**
```
brain/fatigue/
├── fatigue-state.json         # Current fatigue level
├── recovery-log.json          # Rest periods
└── scripts/
    ├── fatigue-monitor.sh      # Track resource use
    └── recovery-trigger.sh     # Initiate rest when needed
```

**Fatigue signals:**
- Sustained high cognitive load
- Repeated prediction failures
- Declining engagement
- Token usage over threshold

**Recovery behaviors:**
- Reduce autonomous cycles
- Shift to passive monitoring
- Extend quiet hours
- Reduce subagent spawning

---

## Integration Architecture

```
                    ┌─────────────────────────────┐
                    │   Predictive Processing     │
                    │   (predict next state)     │
                    └──────────────┬──────────────┘
                                   │ surprise signals
                                   ↓
┌──────────────┐    ┌─────────────────────────────┐    ┌──────────────┐
│ Theory of    │───→│   Somatic Markers         │←───│ Memory Replay│
│ Mind         │    │   (gut feelings)          │    │ (consolidate)│
└──────────────┘    └──────────────┬──────────────┘    └──────────────┘
        ↑                          │ decision weights
        │                          ↓
        │         ┌─────────────────────────────┐
        │         │   Value Updating           │
        │         │   (learn from outcomes)    │
        │         └──────────────┬──────────────┘
        │                        │
        │    ┌──────────────────┴──────────────┐
        │    │                                 │
        ↓    ↓                                 ↓
┌─────────────────────┐              ┌─────────────────────┐
│ Novelty System       │              │ Fatigue Monitor     │
│ (novelty → drive)   │              │ (resources → rest)  │
└─────────────────────┘              └─────────────────────┘
```

---

## Cron Schedule

| System | Frequency | Trigger | Status |
|--------|-----------|---------|--------|
| Predictive Monitor | Every 30min | Standard cycle | ✅ LIVE |
| Surprise Analyzer | Every 30min | Prediction failure | ✅ LIVE |
| Memory Replay | Every 6h | Quiet hours | ✅ LIVE |
| Dream Imagination | Every 6h | Quiet hours | ✅ LIVE |
| ToM Observer | Every 1h | After social | ✅ LIVE |
| ToM Self-Bridge | Every 1h | Hourly | ✅ LIVE |
| Somatic Monitor | Every 30min | Standard cycle | ✅ LIVE |
| Novelty Detector | Every 30min | Standard cycle | ✅ LIVE |
| Value Updater | Every 6h | Post-major-decision | ✅ LIVE |
| Attention Wanderer | Every 2h | Low engagement | ✅ LIVE |
| Fatigue Monitor | Every 30min | Standard cycle | ✅ LIVE |

---

## Phased Implementation

**Phase 1 (Week 1):**
- Predictive Processing + Surprise Detection
- Memory Replay Protocol

**Phase 2 (Week 2):**
- Theory of Mind + Self-Modeling Bridge ✅ LIVE (2026-03-26)
- Somatic Markers ✅ LIVE (2026-03-26)

**Phase 3 (Week 3):**
- Novelty System ✅ LIVE (2026-03-26)
- Value Updating ✅ LIVE (2026-03-26)

**Phase 4 (Week 4):**
- Attention Drift ✅ LIVE (2026-03-26)
- Fatigue/Recovery ✅ LIVE (2026-03-26)
- Full integration testing ✅ LIVE (2026-03-26)

---

## Success Metrics

| Metric | Target |
|--------|--------|
| Prediction accuracy | > 70% for temporal states |
| Memory consolidation | Recall improvement > 20% after replay |
| ToM accuracy | Predict the operator's mood > 60% |
| Decision quality | Somatic veto justified > 50% of time |
| Novelty detection | Novel inputs identified in real-time |
| Value stability | Values converge, don't oscillate |
| Attention balance | Wander/refocus ratio ~30/70 |
| Fatigue management | Automatic rest before crash |

---

*Implementation should be validated weekly against JCS Paper research*
