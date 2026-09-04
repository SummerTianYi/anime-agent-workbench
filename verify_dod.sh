#!/usr/bin/env bash
# Final DoD verification: sabotage drill + 3x strict acceptance + push retry.
set -u
cd "$(dirname "$0")"
echo "=== sabotage drill ==="
python acceptance/sabotage_drill.py | tail -1 || exit 1
echo "=== unit tests ==="
python -m unittest discover -s tests 2>&1 | tail -3 || exit 1
echo "=== run_all --strict x3 ==="
for i in 1 2 3; do
  echo "--- round $i ---"
  python acceptance/run_all.py --strict 2>&1 | grep -E "VERDICT"
done
echo "=== push retry ==="
for i in 1 2 3; do
  if git push 2>&1 | tail -1; then
    if git status -sb | grep -q ahead; then sleep 10; else echo "PUSHED"; break; fi
  else
    sleep 15
  fi
done
git log --oneline -5
