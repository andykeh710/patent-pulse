#!/usr/bin/env bash
# Hits 9 production routes and exits non-zero if any returns 5xx.
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
for route in "${ROUTES[@]}"; do
  code=$(curl -sS -o /dev/null -w "%{http_code}" --max-time 10 "$BASE$route" || echo "000")
  if [[ "$code" =~ ^5 ]] || [[ "$code" == "000" ]]; then
    echo "FAIL  $code  $route"
    FAIL=$((FAIL + 1))
  else
    echo "OK    $code  $route"
  fi
done
exit "$FAIL"
