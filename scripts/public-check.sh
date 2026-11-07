#!/usr/bin/env bash
# Refuse to publish anything that looks private. Run before pushing a public copy.
#
# AGENTS.md is a session handoff and is never published, so it is not scanned.
#
#   ./scripts/public-check.sh            scan the working tree
#   ./scripts/public-check.sh --all      also scan every commit in the history
#
# Exits 1 and prints file:line for anything it finds.

set -uo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT" || exit 1

# Personal identity, machine identity, credentials.
PATTERNS=(
  'cm\.rawlings|Chris Rawlings'
  '/home/[a-z][a-z0-9_-]+/'                       # somebody's home directory
  'CM\.Rawlings|@gmail\.com|@outlook\.com'
  'bluecloud|tactical|fusionpbx|rmm-relay'        # work context
  'chris-[a-z0-9-]+\.local'                       # hostname
  'HNTL[0-9]+|serial (…|[0-9]{4,})'               # device serials
  'sk-ant-[A-Za-z0-9]|ghp_[A-Za-z0-9]|gho_[A-Za-z0-9]|github_pat_|AKIA[0-9A-Z]{8}'
  'https://[A-Za-z0-9_-]+:[^@/[:space:]]+@'       # credentials in a URL
  '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b'               # IPv4
  '\b([0-9a-fA-F]{2}:){5}[0-9a-fA-F]{2}\b'        # MAC address
  'BEGIN [A-Z ]*PRIVATE KEY'
)

# Things that are fine even though they match a pattern above.
ALLOW='teknoprep/vitals|github\.com/teknoprep|127\.0\.0\.1|allow_token_by_default|hide_token_restore|Portal\.Secret|sudo/password|wrong-password|password text|make/model/serial|monitor_desc|tokens? (redacted|in a URL)|::1'

status=0
scan() {
  local label="$1"
  local hits
  hits=$(grep -rInE --exclude=public-check.sh --exclude=AGENTS.md "$(IFS='|'; echo "${PATTERNS[*]}")" "$label" 2>/dev/null | grep -vE "$ALLOW")
  if [[ -n $hits ]]; then
    printf '%s\n' "$hits"
    status=1
  fi
}

echo "== working tree"
scan --exclude-dir=.git .
echo "== files that should never be here"
for forbidden in \
  home/.config/rclone/rclone.conf \
  home/.config/gh/hosts.yml \
  home/.ssh \
  home/.pi/agent/auth.json; do
  if [[ -e $forbidden ]]; then
    echo "$forbidden"
    status=1
  fi
done

# runtime state is fine only where it is a hand-written toggle
if [[ -d home/.local/state ]]; then
  stray=$(find home/.local/state -mindepth 1 -maxdepth 1 ! -name omarchy)
  [[ -n $stray ]] && { echo "$stray"; status=1; }
  stray=$(find home/.local/state/omarchy -mindepth 1 -maxdepth 1 ! -name toggles 2>/dev/null)
  [[ -n $stray ]] && { echo "$stray"; status=1; }
fi

if [[ ${1:-} == "--all" ]]; then
  echo "== history"
  if [[ -d .git ]]; then
    git log -p --all | grep -nE "$(IFS='|'; echo "${PATTERNS[*]}")" | grep -vE "$ALLOW" | head -20
    [[ ${PIPESTATUS[0]} -eq 0 ]] && status=1
  fi
fi

if (( status )); then
  echo
  echo "FAIL: private data above. Do not publish until it is gone."
else
  echo
  echo "PASS: nothing private found."
fi
exit "$status"
