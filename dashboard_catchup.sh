#!/bin/bash
# Catch the FullyScale Weekly Dashboard up to today, from whatever state it is in.
#
# Every step is idempotent and self-healing: weekly_meta_inputs.py fills EVERY
# missing week (not one per run, which is why the old meta_ads_weekly_pull.py
# left a 3-week hole after the Aug 2026 token outage), and the ad-set refresh
# rebuilds Ad Set Overview + Live Meta from scratch each time. Safe to run twice.
#
# Run it after refreshing the Meta token in the ad-analytics Config tab, or let
# the Monday dashboard-freshness job run it for you.
#
# Usage: dashboard_catchup.sh [--probe-only]
set -uo pipefail

ROOT="/Users/Logan/ClaudeCode"
PY=$(command -v /opt/homebrew/bin/python3 || command -v python3)
NODE=$(command -v /opt/homebrew/bin/node || command -v /usr/local/bin/node || command -v node)
STATE="$HOME/n8n/state"
FAILED=()

step() { printf '\n=== %s ===\n' "$1"; }

if [ "${1:-}" = "--probe-only" ]; then
    exec "$PY" "$ROOT/automation-scripts/dashboard_freshness.py" --no-stamp
fi

step "Weekly Inputs — fill every closed week from the Meta API"
if "$PY" "$ROOT/automation-scripts/weekly_meta_inputs.py"; then
    [ -d "$STATE" ] && date +%F > "$STATE/meta.last"
else
    FAILED+=("weekly_meta_inputs.py (Weekly Inputs — check the Meta token in Config!B2)")
fi

step "Ad Set Overview + Live Meta — rebuild from Meta Raw and Lead Log"
if (cd "$ROOT/sheets-mcp" && "$NODE" refresh-ad-set-overview.js); then
    [ -d "$STATE" ] && date +%F > "$STATE/adset.last"
else
    FAILED+=("refresh-ad-set-overview.js (Ad Set Overview / Live Meta)")
fi

step "Freshness probe — re-check every feed and re-stamp the dashboard"
"$PY" "$ROOT/automation-scripts/dashboard_freshness.py" || FAILED+=("dashboard_freshness.py")

if [ ${#FAILED[@]} -gt 0 ]; then
    printf '\nCATCHUP INCOMPLETE — %d step(s) failed:\n' "${#FAILED[@]}"
    printf '  - %s\n' "${FAILED[@]}"
    exit 1
fi
printf '\nCATCHUP OK — all steps completed.\n'
