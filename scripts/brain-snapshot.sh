#!/bin/bash
# brain-snapshot.sh — Compact one-line-per-system brain state summary + canonical brain-state.json
# Reads from BIOMIMETIC BRAIN system files (brain/somatic/, brain/fatigue/, etc.)
# These are the live signal sources used by the decision gate.
set -euo pipefail

BRAIN="$HOME/.hermes/agents/palantir/brain"
OUT="$HOME/.hermes/agents/palantir/brain-state.json"
SCRIPT_DIR="$HOME/.hermes/agents/palantir/scripts"

# 1. Generate the canonical 22-system brain-state.json from all subsystem files.
#    This is the authoritative source for the decision gate.
#    Cron agents (morning/midday/evening) write to brain-snapshots/daily/ — NOT here.
python3 "$SCRIPT_DIR/generate-brain-state.py"

# Helper: extract JSON value
jval() { python3 -c "import sys,json; d=json.load(open('$1')); print($2)" 2>/dev/null || echo "?"; }

echo "🧠 BIOMIMETIC BRAIN STATE $(date +%H:%M)"
echo "---"

# Somatic (gut/energy/confidence/tension/valence)
if [ -f "$BRAIN/somatic/markers.json" ]; then
  gut=$(jval "$BRAIN/somatic/markers.json" "d.get('gut_feeling','?')")
  energy=$(jval "$BRAIN/somatic/markers.json" "round(d.get('energy',0),2)")
  confidence=$(jval "$BRAIN/somatic/markers.json" "round(d.get('confidence',0),2)")
  tension=$(jval "$BRAIN/somatic/markers.json" "round(d.get('tension',0),2)")
  valence=$(jval "$BRAIN/somatic/markers.json" "round(d.get('valence',0.5),2)")
  echo "SOMATIC: gut=$gut energy=$energy confidence=$confidence tension=$tension valence=$valence"
fi

# Fatigue (recovery_needed, fatigue_level, sustainable)
if [ -f "$BRAIN/fatigue/fatigue-state.json" ]; then
  fatigue=$(jval "$BRAIN/fatigue/fatigue-state.json" "round(d.get('fatigue_level',0),2)")
  recovery=$(jval "$BRAIN/fatigue/fatigue-state.json" "d.get('recovery_needed',False)")
  sustain=$(jval "$BRAIN/fatigue/fatigue-state.json" "d.get('sustainable',True)")
  vta=$(jval "$BRAIN/fatigue/fatigue-state.json" "round(d.get('vta_drive',0.57),2)")
  echo "FATIGUE: level=$fatigue recovery=$recovery sustainable=$sustain vta=$vta"
fi

# Novelty / VTA Boost
if [ -f "$BRAIN/dopamine/novelty-state.json" ]; then
  novelty=$(jval "$BRAIN/dopamine/novelty-state.json" "round(d.get('novelty_seeking',0.5),2)")
  vtaboost=$(jval "$BRAIN/dopamine/novelty-state.json" "round(d.get('vta_boost',0),2)")
  echo "DOPAMINE/VTA: novelty=$novelty vta_boost=$vtaboost"
fi

# SCN (circadian phase, quiet hours)
if [ -f "$BRAIN/scn/scn-state.json" ]; then
  phase=$(jval "$BRAIN/scn/scn-state.json" "d.get('phase','?')")
  quiet=$(jval "$BRAIN/scn/scn-state.json" "d.get('quiet_hours',False)")
  localh=$(jval "$BRAIN/scn/scn-state.json" "d.get('localHour','?')")
  echo "SCN: phase=$phase quiet_hours=$quiet local_hour=$localh"
fi

# Attention
if [ -f "$BRAIN/attention/attention-state.json" ]; then
  mode=$(jval "$BRAIN/attention/attention-state.json" "d.get('mode','?')")
  echo "ATTENTION: mode=$mode"
fi

# Values
if [ -f "$BRAIN/values/values-state.json" ]; then
  top=$(jval "$BRAIN/values/values-state.json" "list(d.get('values',{}).keys())[0] if d.get('values') else '?'")
  echo "VALUES: top=$top"
fi

# Dream/Memory Replay
if [ -f "$BRAIN/hippocampus/dream-state.json" ]; then
  videos=$(jval "$BRAIN/hippocampus/dream-state.json" "d.get('stats',{}).get('videos_remaining_today','?')")
  total=$(jval "$BRAIN/hippocampus/dream-state.json" "d.get('stats',{}).get('total_dreams','?')")
  echo "MEMORY/DREAM: videos_today=$videos total_dreams=$total"
fi

# Prefrontal Cortex — Emergent Interests
if [ -f "$BRAIN/prefrontal/interest-emergence-state.json" ] 2>/dev/null; then
  :
fi
PREFC="$BRAIN/prefrontal/interest-emergence-state.json"
if [ -f "$PREFC" ]; then
  emerged=$(jval "$PREFC" "len(d.get('emerged_interests',[]))")
  convictions=$(jval "$PREFC" "len(d.get('convictions',[]))")
  passions=$(jval "$PREFC" "len(d.get('passions',[]))")
  top_interest=$(jval "$PREFC" "d.get('emerged_interests',[{}])[0].get('concept','?') if d.get('emerged_interests') else 'none'")
  top_conviction=$(jval "$PREFC" "d.get('convictions',[{}])[0].get('concept','?') if d.get('convictions') else 'none'")
  top_passion=$(jval "$PREFC" "d.get('passions',[{}])[0].get('concept','?') if d.get('passions') else 'none'")
  echo "PREFRONTAL: interests=$emerged convictions=$convictions passions=$passions"
  echo "  top_interest=$top_interest top_conviction=$top_conviction top_passion=$top_passion"
fi

# Predictive / Surprise
if [ -f "$BRAIN/predictive/surprise-log.json" ]; then
  acc=$(jval "$BRAIN/predictive/surprise-log.json" "round(d.get('stats',{}).get('accuracy_rate',0),2)")
  matches=$(jval "$BRAIN/predictive/surprise-log.json" "d.get('stats',{}).get('matches',0)")
  mismatches=$(jval "$BRAIN/predictive/surprise-log.json" "d.get('stats',{}).get('mismatches',0)")
  echo "SURPRISE: accuracy=$acc matches=$matches mismatches=$mismatches"
fi

# Decision Gate
AUTONOMY="$BRAIN/autonomy-scope.json"
if [ -f "$AUTONOMY" ]; then
  scope=$(jval "$AUTONOMY" "d.get('scope','?')")
  gut_scope=$(jval "$AUTONOMY" "d.get('gut','?')")
  ts=$(jval "$AUTONOMY" "d.get('timestamp','?')")
  echo "GATE: scope=$scope gut=$gut_scope ts=$ts"
else
  echo "GATE: scope=unknown (run gate first)"
fi

echo "---"
echo "Snapshot complete"

# P3 Systems
CEREB="$BRAIN/cerebellum/cerebellum-state.json"
if [ -f "$CEREB" ]; then
  procedural=$(jval "$CEREB" "len(d.get('procedural_habits',[]))")
  echo "CEREBELLUM: procedural=$procedural"
fi

LC="$BRAIN/lc/lc-state.json"
if [ -f "$LC" ]; then
  arousal=$(jval "$LC" "d.get('current_arousal','?')")
  state=$(jval "$LC" "d.get('behavioral_state','?')")
  echo "LC: arousal=$arousal state=$state"
fi

SERO="$BRAIN/raphé/serotonin-state.json"
if [ -f "$SERO" ]; then
  level=$(jval "$SERO" "d.get('current_serotonin','?')")
  patience=$(jval "$SERO" "d.get('patience_state','?')")
  echo "SEROTONIN: level=$level patience=$patience"
fi

SOMA="$BRAIN/somatosensory/somatosensory-state.json"
if [ -f "$SOMA" ]; then
  battery=$(jval "$SOMA" "d.get('battery_level','?')")
  thermal=$(jval "$SOMA" "d.get('thermal_state','?')")
  echo "SOMATOSENSORY: battery=$battery thermal=$thermal"
fi

NAc="$BRAIN/nac/nac-state.json"
if [ -f "$NAc" ]; then
  urgency=$(jval "$NAc" "d.get('current_urgency','?')")
  echo "NAc: urgency=$urgency"
fi

DMN="$BRAIN/dmn/dmn-state.json"
if [ -f "$DMN" ]; then
  traits=$(jval "$DMN" "d.get('self_model',{}).get('core_traits',[])[:3]")
  discrepancy=$(jval "$DMN" "d.get('self_model',{}).get('self_discrepancy','?')")
  echo "DMN: traits=$traits discrepancy=$discrepancy"
fi
