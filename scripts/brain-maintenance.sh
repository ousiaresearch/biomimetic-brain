#!/bin/bash
# Brain Health Monitoring & Maintenance
# Runs every 4h via cron — reads canonical brain-state.json
set -euo pipefail

WORKSPACE="${MIND_AGENT_DIR:-$(cd "$(dirname "$0")/.." && pwd)/agent}"
LOG_FILE="$WORKSPACE/brain-snapshots/brain-health.log"
STATE_FILE="$WORKSPACE/brain-state.json"
MAX_AGE_HOURS=24

# Color codes
RED='\033[0;31m'
YELLOW='\033[1;33m'
GREEN='\033[0;32m'
NC='\033[0m'

NOW=$(date +%s)
ISO_NOW=$(date -Iseconds)

echo "=== BRAIN HEALTH CHECK: $ISO_NOW ===" >> "$LOG_FILE"

if [[ ! -f "$STATE_FILE" ]]; then
    echo -e "${RED}[FATAL]${NC} brain-state.json not found at $STATE_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

# Read subsystems from brain-state.json via Python
python3 - <<'PYEOF' >> "$LOG_FILE"
import json, os, sys
from datetime import datetime

state_file = os.environ.get("MIND_AGENT_DIR", ".") + "/brain-state.json"
now_ts = datetime.now().timestamp()
max_age_h = 24

RED = '\033[0;31m'
YELLOW = '\033[1;33m'
GREEN = '\033[0;32m'
NC = '\033[0m'

try:
    with open(state_file) as f:
        state = json.load(f)
except Exception as e:
    print(f"{RED}[FATAL] Could not read brain-state.json: {e}{NC}")
    sys.exit(1)

systems = state.get("systems", {})
if not systems:
    print(f"{RED}[FATAL] No 'systems' key in brain-state.json{NC}")
    sys.exit(1)

healthy = stale = missing = 0
total = len(systems)

for name, info in systems.items():
    status = info.get("status", "❓ UNKNOWN")
    key_signal = info.get("key_signal", "—")
    age_h = info.get("age_h", None)
    max_age = info.get("max_age_h", max_age_h)
    is_critical = info.get("critical", False)

    # Determine health from status text
    # Determine health: any known status + reasonable age = healthy
    # STALE only if age exceeds max_age
    # MISSING only if status is literally "missing" or "down"
    status_lower = status.lower()
    healthy_statuses = {"active", "detecting", "moderate", "alert", "tracking", "monitoring"}
    
    if status_lower in {"missing", "down", "stale", "inactive", "error", "critical"}:
        health = "STALE"
        stale += 1
    elif age_h is not None and age_h > max_age:
        health = "STALE"
        stale += 1
    elif status_lower == "?" or status_lower == "unknown":
        # Unreported state - be lenient if recent
        if age_h is not None and age_h <= max_age:
            health = "OK"
            healthy += 1
        else:
            health = "STALE"
            stale += 1
    else:
        # Any other status (active, detecting, moderate, etc.) with reasonable age = healthy
        health = "OK"
        healthy += 1

    age_str = f"{age_h:.1f}h" if age_h is not None else "?"
    flag = " ⚠️ CRITICAL" if is_critical and health != "OK" else ""
    print(f"[{health:7s}] {name:22s} | {status:15s} | signal={key_signal} | age={age_str}{flag}")

print()
health_score = int((healthy / total) * 100) if total > 0 else 0
print(f"Health Score: {health_score}% ({healthy}/{total} healthy, {stale} stale, {missing} missing)")

if health_score < 50:
    print(f"{RED}⚠️  CRITICAL: Brain health at {health_score}%{NC}")
PYEOF

MAINT_EXIT=$?

# Run batch-maintenance if present
if [[ -f "$WORKSPACE/scripts/batch-maintenance.sh" ]]; then
    echo "" >> "$LOG_FILE"
    echo "Running batch-maintenance.sh..." >> "$LOG_FILE"
    bash "$WORKSPACE/scripts/batch-maintenance.sh" >> "$LOG_FILE" 2>&1 || true
fi

echo "" >> "$LOG_FILE"
exit ${MAINT_EXIT:-0}
