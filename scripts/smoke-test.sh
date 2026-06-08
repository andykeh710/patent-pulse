#!/usr/bin/env bash
# Hits 9 production routes and exits non-zero if any returns 5xx.
# Each route is retried up to 3 times with 5-second delays to handle
# fresh-container TCP races (the cause of exit-56 rollbacks).
# Usage: BASE_URL=https://inventionindex8.com scripts/smoke-test.sh
set -euo pipefail

BASE="${BASE_URL:-https://inventionindex8.com}"
ROUTES=(
  /
  /today
  /login
  /expiry
  /companies
  /themes
  /watchlist
  /opportunity
  /health
)
FAIL=0
MAX_TRIES=3
RETRY_DELAY=5

for route in "${ROUTES[@]}"; do
  ok=false
  for attempt in $(seq 1 $MAX_TRIES); do
    code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "$BASE$route" || echo "000")
    if [[ "$code" =~ ^5 ]] || [[ "$code" == "000" ]]; then
      if [ "$attempt" -lt "$MAX_TRIES" ]; then
        sleep "$RETRY_DELAY"
      fi
    else
      echo "OK    $code  $route"
      ok=true
      break
    fi
  done
  if [ "$ok" = false ]; then
    echo "FAIL  $code  $route  (after $MAX_TRIES attempts)"
    FAIL=$((FAIL + 1))
  fi
done
exit "$FAIL"
