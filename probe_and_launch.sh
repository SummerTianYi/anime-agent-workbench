#!/usr/bin/env bash
# Probe GLM endpoint every 5 min; when healthy, launch the live eval once.
cd "$(dirname "$0")"
set -a
. "/d/UserData/Administrator/Documents/Codex/2026-08-28/https-github-com-summertianyi-anime-agent/work/anime-agent-mvp/.env"
set +a
export WORKBENCH_LLM_BASE_URL="$GLM_BASE_URL" WORKBENCH_LLM_API_KEY="$GLM_API_KEY" WORKBENCH_LLM_MODEL="$GLM_MODEL"

for i in $(seq 1 24); do  # up to 2 hours of probing
  code=$(python - <<'EOF'
import os, urllib.request, json, time
t0 = time.time()
req = urllib.request.Request(
    os.environ["WORKBENCH_LLM_BASE_URL"].rstrip("/") + "/chat/completions",
    data=json.dumps({"model": os.environ["WORKBENCH_LLM_MODEL"],
                     "messages": [{"role": "user", "content": "reply ok"}],
                     "stream": False}).encode(),
    headers={"Content-Type": "application/json",
             "Authorization": "Bearer " + os.environ["WORKBENCH_LLM_API_KEY"]})
try:
    json.loads(urllib.request.urlopen(req, timeout=60).read())
    print("OK")
except Exception as exc:
    print("FAIL", exc)
EOF
)
  echo "$(date +%H:%M:%S) probe $i: $code"
  if [[ "$code" == OK* ]]; then
    echo "endpoint healthy - launching live eval"
    python -u acceptance/evals/run_live.py
    echo "LIVE_EVAL_EXIT=$?"
    exit 0
  fi
  sleep 300
done
echo "endpoint never recovered within 2h"
exit 1
