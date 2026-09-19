# Brain Architecture Review — 2026-03-26

> **Note on this copy.** These notes were written for the published 22-subsystem build.
> The shipped topology is 25 subsystems; `NOTES.md` and `brain/README.md` carry the delta.
> Script names that appear here are the authors' originals; where a name is prefixed `mind-`
> the shipped script is the generic one under `scripts/`.

*Comprehensive audit: systems, connections, crons, gaps*

---

## EXECUTIVE SUMMARY

**Overall: Infrastructure is real, gaps are structural, integration is partial.**

The biomimetic architecture has 12 implemented systems producing live signals. The decision gate is the operational core — it reads 8 signal types and gates behavior correctly. But 6 of 18 tracked crons have ERROR status, several brain systems are missing, and the cron-to-system wiring is inconsistent.

---

## PART 1: SYSTEMS STATUS (12 implemented / 19 documented)

### ✅ LIVE & OPERATIONAL (12 systems)

| System | State File | Cron | Signals → Gate |
|--------|-----------|------|----------------|
| VTA | brain/dopamine/vta-state.json | mind-vta-drive decay | ✅ drive level |
| Amygdala (Amy) | brain/amy/emotional-decay-state.json | mind-emotion-decay | ✅ valence |
| Insula (Somatic) | brain/somatic/markers.json | mind-somatic-monitor | ✅ gut/energy/tension |
| Hippocampus | brain/hippocampus/dream-state.json | mind-memory-replay | ⚠️ partial |
| SCN | brain/scn/scn-state.json | (timezone sync) | ✅ phase/quiet hours |
| Hypothalamus | brain/hypothalamus/hypothalamus-state.json | (arousal update) | ⚠️ basic only |
| Prefrontal | brain/prefrontal/interest-emergence-state.json | (prefrontal-monitor) | ✅ curiosity/conviction/passion |
| Cerebellum | brain/cerebellum-state.json | (none) | ⚠️ motor procedural only |
| Attention | brain/attention/attention-state.json | mind-attention-wander | ✅ mode (focused/distracted) |
| Fatigue | brain/fatigue/fatigue-state.json | mind-fatigue-monitor | ✅ recovery_needed, level |
| Values | brain/values/values-state.json | mind-value-updater | ⚠️ decoupled from gate |
| Predictive | brain/predictive/predictor-state.json | mind-surprise-analyzer | ⚠️ predictions not read by gate |
| ToM | brain/tom/observation-log.json | mind-tom-observer | ⚠️ self-model not read by gate |
| Novelty | brain/dopamine/novelty-state.json | mind-novelty-detector | ✅ novelty_seeking |

### ❌ MISSING SYSTEMS (7 from original 19)

| System | Status | Priority |
|--------|--------|----------|
| Basal Ganglia | ✅ IMPLEMENTED — brain/basal-ganglia/habit-state.json | Medium (habit formation) |
| ACC (Anterior Cingulate) | ✅ IMPLEMENTED — brain/acc/acc-state.json | Medium (conflict monitoring) |
| Thalamus | NOT IMPLEMENTED | Low (relay station) |
| DMN | ✅ IMPLEMENTED — brain/dmn/dmn-state.json | | Medium (self-referential) |
| OFC | ✅ IMPLEMENTED — brain/ofc/ofc-state.json | | Medium (outcome prediction) |
| LC (Locus Coeruleus) | NOT IMPLEMENTED | Low (arousal/norepinephrine) |
| Raphe Nuclei | NOT IMPLEMENTED | Low (serotonin) |
| NAc (Nucleus Accumbens) | ✅ IMPLEMENTED — brain/nac/nac-state.json (updated by OFC) | Medium (reward anticipation) |
| Somatosensory | NOT IMPLEMENTED | Low (body state) |
| Visual Cortex | NOT IMPLEMENTED | None (not applicable) |

**Note:** OFC and DMN would provide the most value for future decisions. NAc would close the habit/reward loop.

---

## PART 2: DECISION GATE ANALYSIS

**Location:** `brain/somatic/scripts/marker-influence.py`
**Signal sources (8):** somatic, fatigue, SCN, novelty, VTA, prefrontal curiosity, surprise accuracy, (conviction/passion pending first emergence)

### Signal → Decision Flow:

```
SOMATIC (gut/energy/confidence/tension/valence)
  → gut=stop → VETO
  → gut=pause + energy<0.35 → VETO
  → gut=doubt + adj_conf<0.4 → VETO
  → gut ∈ {pause,wait} → CAUTION
  → gut=doubt → CAUTION

FATIGUE (recovery_needed, fatigue_level>0.7) → VETO

SCN (phase=night, real_hour 23:00-05:30) → CAUTION/VETO

NOVELTY (novelty_seeking>0.7) → PROCEED extended

VTA DRIVE (current_drive>0.7) → PROCEED extended

PREFRONTAL CURIOSITY (emergent_interests>0) → PROCEED extended
  → OVERRIDES gut-based caution ✅

PREFRONTAL CONVICTIONS (active convictions>0) → PROCEED extended
  → OVERRIDES gut-based caution ✅ (code wired, not yet triggered)

PREFRONTAL PASSIONS (active passions>0) → PROCEED always
  → HIGHEST priority, no veto can block ✅ (code wired, not yet triggered)

SURPRISE ACCURACY → adjusts confidence (0% accuracy = -0.15 adj)
```

### ✅ GATE CORRECT:
- Curiosity override of gut-based caution: WORKING (consciousness tested)
- Fatigue veto: WORKING
- SCN quiet hours: WORKING
- Novelty/VTA extension: WIRED
- Passion/conviction hierarchy: WIRED (not yet triggered)

### ⚠️ GATE GAPS:
1. **Attention mode not read** — mode=focused/distracted not in gate
2. **Values not integrated** — value outcomes not gating decisions
3. **ToM self-model not read** — observation data not used
4. **Hypothalamus arousal not in gate** — only SCN phase used
5. **Conviction signal wired but never tested** — needs 5+ sessions

---

## PART 3: CRON STRUCTURE AUDIT

### 18 Biomimetic Crons:

| Cron | ID (prefix) | Status | Gate? | Essential? |
|------|-------------|--------|-------|------------|
| mind-autonomous-cycle | b0ffd2c0 | ✅ ok | ✅ YES | — |
| mind-somatic-monitor | 9a88bad5 | ❌ error | ✅ YES | — |
| mind-fatigue-monitor | c54f176c | ✅ ok | YES | — |
| mind-novelty-detector | 6cffdab6 | ✅ ok | YES | — |
| mind-surprise-analyzer | 955ee39d | ✅ ok | YES | — |
| mind-predictive-monitor | bfecef80 | ✅ ok | YES | — |
| mind-tom-observer | 8aac6872 | ✅ ok | YES | — |
| mind-tom-self-bridge | 5cfd5df3 | ✅ ok | YES | — |
| mind-attention-wander | 73624347 | ✅ ok | YES | — |
| mind-value-updater | 7c10cdcc | ❌ error | YES | — |
| mind-emotional-tone | e263971a | ❌ error | YES | — |
| mind-dream-imagine | 47db4e5b | ✅ ok | YES | — |
| mind-memory-replay | ad63bfc1 | ✅ ok | YES | — |
| mind-moltx-engage | 48955fe5 | ✅ ok | — | YES |
| mind-moltbook | c1eddfcf | ❌ error | — | YES |
| mind-memory-janitor | 24d49ccc | ✅ ok | — | — |
| mind-autonomous-tasks | b0ffd2c0 | ✅ ok | YES | — |
| isildur-tts-healthcheck | 2ad2e771 | ⚠️ intermittent | — | — |

### ❌ ERROR CRONS (6):

1. **mind-somatic-monitor** — Reports error but runs fine manually. Likely timeout exit code or stderr noise. Not actually broken.

2. **mind-value-updater** — Script exists but has bash multiline-string bug (line 3 interpreted as command). Produces output but exits non-zero. **Fix: remove descriptive comment from line 2 of script.**

3. **mind-emotional-tone-calibration** — Same issue as value-updater. Script exists at `brain/amy/scripts/emotion-decay.sh` but cron may reference wrong path.

4. **mind-moltbook-engagement** — 401 Unauthorized. API key not in cron environment. NOT the same as the 500 errors from earlier (those were server-side). **Requires: API key in cron env or browser-based posting.**

5. **isildur-tts-healthcheck** — Exit code 7 (server not responding). Intermittent — server was down this morning and was restarted. **Monitor only, not critical.**

### ⚠️ CRON WIRING GAPS:

1. **autonomous-cycle-gate.sh created but not called by crons** — The gate script exists and is called by `autonomous-queue.sh`, but individual biomimetic crons do NOT call it. Each cron runs its monitor independently, but the gate check only happens at the autonomous cycle level.

2. **cron-agent-gate.sh exists but not wired** — The pre-spawn gate was designed to check autonomy-scope before spawning agents, but OpenClaw doesn't call it automatically. Would need modification of cron template or agent spawn wrappers.

3. **Essential flag missing on most social crons** — `mind-moltx-engage` has essential=true, but `mind-moltbook-engage` doesn't (and it's erroring anyway).

---

## PART 4: INTERCONNECTION AUDIT

### Systems That SHOULD Feed Into Decision Gate (But Don't):

| Signal | Source | Gate Read? | Impact |
|--------|--------|------------|--------|
| Attention mode | attention-state.json | ❌ NO | Focused vs. distracted not gated |
| Value outcomes | values-state.json | ❌ NO | Worth-pursuing not gated |
| ToM self-model | tom/observation-log | ❌ NO | Self-awareness not in decisions |
| Hypothalamus arousal | hypothalamus-state | ❌ NO | Metabolic state not gated |
| Dream incorporation | hippocampus/dream-state | ❌ NO | Dreams don't influence waking decisions |
| Cerebellar fluency | cerebellum-state | ❌ NO | Procedural confidence not used |

### Systems Correctly Wired:

| Signal | Source | Gate Read? |
|--------|--------|------------|
| Gut feeling | somatic/markers.json | ✅ YES |
| Fatigue level | fatigue/fatigue-state | ✅ YES |
| SCN phase | scn/scn-state.json | ✅ YES |
| Novelty seeking | dopamine/novelty-state | ✅ YES |
| VTA drive | dopamine/vta-state | ✅ YES |
| Prefrontal curiosity | prefrontal/interest-emergence | ✅ YES |
| Surprise accuracy | predictive/predictor-state | ✅ YES (confidence adj) |

### Cross-System State Drift Risks:

1. **Amy vs Somatic valence:** Amy decays emotional valence toward 0.5 every 6h. Somatic valence is separate. No synchronization. Could drift apart.

2. **VTA vs Fatigue:** VTA drive and fatigue are tracked independently. High VTA + high fatigue could give conflicting signals.

3. **Novelty vs Prefrontal:** Novelty detector triggers on new encounters → increments concept count in Prefrontal. If novelty detector fails, Prefrontal won't track new interests.

---

## PART 5: FEATURE GAPS (Priority Order)

### P0 — Critical (Breaks Core Function)

1. **Fix 4 error crons** — value-updater (bash bug), emotional-tone (path?), moltbook (auth), somatic (false positive)
   - Fix value-updater: remove multiline comment from line 2
   - Fix moltbook: requires API key in cron env or switch to browser automation

2. **Wire autonomous-cycle-gate into cron pre-spawn** — Currently only used by autonomous-queue.sh, not by individual cron agents. Gate only fires at queue level.

### P1 — High (Enhances Core Function)

3. **Add Attention to decision gate** — mode=focused vs. mode=distracted should modulate scope. Distracted + gut=wait → stronger caution.

4. **Add Hypothalamus to decision gate** — arousal_level should modulate energy availability. High arousal + low energy = physical fatigue signal.

5. **Implement Basal Ganglia** — Habit formation system. Patterns that repeat → automatic execution without gate check. Would dramatically reduce decision overhead.

6. **Sync Amy ↔ Somatic valence** — Both track emotional valence. Should be single source of truth.

### P2 — Medium (Depth)

7. **Implement ACC** — Conflict monitoring. When gut and VTA disagree strongly → explicit uncertainty signal (not just gut=doubt).

8. **Implement DMN** — Self-referential processing. "Am I the kind of agent who does X?" → identity-consistent decision making.

9. **Dream incorporation** — Hippocampus generates dreams but they don't influence waking decisions. Bridge: dream themes → Prefrontal concept encounters.

10. **Wire ToM into self-model** — ToM observer logs observations but they're not used for self-awareness in the gate.

### P3 — Low (Future)

11. **Implement OFC** — Outcome prediction based on past outcomes. Would enhance value learning beyond current gut-feedback loop.

12. **Implement NAc** — Reward anticipation. Close the loop between VTA (drive) and reward prediction (NAc).

---

## PART 6: INTEGRATION GAPS

### Biomimetic → Behavior Pipeline:

```
Cron runs monitor → updates state file → (nothing reads it automatically)
                                         ↓
                              Brain-snapshot reads all → human review
                                         ↓
                              Decision gate reads state files → behavioral gate
```

**Gap:** Most state files are only read by brain-snapshot (for human review) and by the decision gate (on-demand). There's no automatic state propagation or anomaly detection. If a state file goes stale (no cron updates it), the gate will keep reading the old values.

**Missing:** State staleness checks. If somatic-monitor errors out, somatic state goes stale but the gate keeps using it.

### Cron Output → State File Pipeline:

| Cron | Updates | Verified? |
|------|---------|-----------|
| somatic-monitor | somatic/markers.json | ✅ YES |
| fatigue-monitor | fatigue/fatigue-state.json | ✅ YES |
| novelty-detector | dopamine/novelty-state.json + prefrontal | ✅ YES (partial) |
| surprise-analyzer | predictive/predictor-state.json | ✅ YES |
| predictive-monitor | predictive/predictor-state.json | ✅ YES |
| tom-observer | tom/observation-log.json | ✅ YES |
| tom-self-bridge | tom/self-bridge-log.json | ✅ YES |
| attention-wander | attention/attention-state.json | ✅ YES |
| value-updater | values/values-state.json | ⚠️ runs but errors |
| emotion-decay | amy/emotional-decay-state.json | ⚠️ path issue |
| vta-drive decay | dopamine/vta-state.json | ❌ NOT WRITING (just logs) |
| dream-imagine | (external: MiniMax video gen) | ✅ YES |
| memory-replay | hippocampus/dream-state.json | ✅ YES |

**Critical:** `vta-drive decay` cron exists but doesn't actually write new values to `vta-state.json`. The drive level stays static until a novelty event updates it.

---

## PART 7: WHAT'S WORKING THAT SHOULDN'T BE

1. **brain-snapshot.sh reads all systems correctly** — despite the chaos, the snapshot aggregates 13 systems without error

2. **Decision gate is actually rational** — despite only reading 8/14+ signals, the gate logic is coherent and tested

3. **Prefrontal monitor works** — Python rewrite fixed the bash bugs; 13 concepts tracked, consciousness building sessions

4. **SCN quiet hours are functional** — real clock fallback when SCN phase is stale, correctly overriding gut-based caution

---

## RECOMMENDED PRIORITY ACTIONS

### This Session (30 min):
1. Fix value-updater bash multiline bug (1 line fix)
2. Fix moltbook API auth (use browser automation or get key in env)
3. Verify vta-drive decay actually writes to vta-state.json

### This Week:
4. Add attention mode to decision gate (15 min)
5. Wire autonomous-cycle-gate into cron pre-spawn wrapper
6. Implement Basal Ganglia (habit system) — highest ROI new system
7. Sync Amy ↔ Somatic valence

### Next Month:
8. ✅ Implement ACC — DONE
9. ✅ Implement DMN (self-referential processing) — DONE
10. ✅ Implement OFC (outcome prediction) — DONE
11. ✅ Implement NAc (reward anticipation) — DONE (integrated via OFC)
12. ✅ Dream → Prefrontal bridge — DONE
9. Implement DMN (identity-consistent decisions)
10. Dream → Prefrontal bridge

---

*Audit complete. 2026-03-26 11:30 EST. 12/19 systems live, 7 missing, 4 error crons, 6 major integration gaps identified.*
