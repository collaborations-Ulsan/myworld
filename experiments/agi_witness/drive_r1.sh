#!/bin/bash
# Autonomous R1 driver: waits for the dataset build, verifies calibration filled,
# then runs R1 (A/B/C x3 seeds) + ablations (C-ablate-* x2 seeds) + score -> verdict.
# Runs entirely on the NVIDIA API (not the Claude session), so it completes on its own.
set -u
cd /home/user/workspaces/jaewon/myworld/experiments/agi_witness
export NVIDIA_API_KEY=$(grep -oP 'NVIDIA_API_KEY=\K.*' ~/.config/nvidia/api.env 2>/dev/null | tr -d '"')
BUDGET=40000
DS_PID="${1:-}"
log(){ echo "[drive_r1 $(date +%H:%M:%S)] $*"; }

# 1. wait for the dataset build to finish (if a PID was passed)
if [ -n "$DS_PID" ]; then
  log "waiting for dataset build PID $DS_PID…"
  while kill -0 "$DS_PID" 2>/dev/null; do sleep 20; done
fi
# also wait until the three output files exist and are non-empty
for _ in $(seq 1 30); do
  [ -s data/tasks.jsonl ] && [ -s data/ledger.jsonl ] && [ -s data/splits.json ] && break
  sleep 10
done

# 2. verify calibration is non-empty (certs must fit) — hard gate
python3 -c "
import json,sys
s=json.load(open('data/splits.json'))
nc=len(s.get('calibration',[])); ne=len(s.get('eval',[]))
print(f'calibration={nc} eval={ne}')
sys.exit(0 if nc>0 and ne>0 else 3)
" || { log 'FATAL: calibration or eval split empty — aborting R1'; exit 3; }

# 3. clean run ledger
: > results/runs.jsonl
log "=== R1: arms A,B,C x seeds 0,1,2 (budget $BUDGET/arm-seed) ==="
python3 run.py --arms A,B,C --seeds 0,1,2 --budget $BUDGET --out results/runs.jsonl 2>&1 | grep -ivE 'libtinfo'

# 4. ablations — each removes exactly one certificate from arm C
for ab in apex iris descent goen writeback; do
  log "=== ablation C-ablate-$ab x seeds 0,1 ==="
  python3 run.py --arms C --ablate "$ab" --seeds 0,1 --budget $BUDGET --out results/runs.jsonl 2>&1 | grep -ivE 'libtinfo'
done

# 5. score -> pre-registered verdict
log "=== scoring -> verdict ==="
python3 score.py 2>&1 | grep -ivE 'libtinfo'
log "PIPELINE DONE — see results/REPORT.md"
