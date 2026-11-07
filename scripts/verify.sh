#!/usr/bin/env bash
# Post-restore checks. Read-only: prints PASS/FAIL lines, exits non-zero on failure.
#   ./scripts/verify.sh

set -uo pipefail
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fail=0
pass() { printf '  \033[32mPASS\033[0m %s\n' "$*"; }
bad()  { printf '  \033[31mFAIL\033[0m %s\n' "$*"; fail=1; }
warn() { printf '  \033[33mWARN\033[0m %s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }

step "hyprland"
if [[ -z $(hyprctl configerrors 2>/dev/null) ]]; then
  pass "no config errors"
else
  bad "hyprctl configerrors: $(hyprctl configerrors 2>/dev/null | head -3 | tr '\n' ' ')"
fi
grep -q "SUPER + mouse_up" <(omarchy menu keybindings --print 2>/dev/null) \
  && pass "SUPER + wheel binding present" || bad "SUPER + wheel binding missing (bindings.lua not loaded)"

step "monitors"
# No expected layout: monitors belong to the machine, arranged in the Displays
# app. This only reports what is connected, so a missing screen is visible.
if hyprctl monitors -j >/dev/null 2>&1; then
  hyprctl monitors -j | jq -r '.[] | "  \(.name) \(.width)x\(.height)@\(.refreshRate|floor)" \
    + (if .transform == 0 then "" else " (transform \(.transform))" end)'
  pass "$(hyprctl monitors -j | jq 'length') monitor(s) reported by Hyprland"
else
  warn "hyprctl not available, cannot report monitors"
fi

step "deskstate"
for unit in deskstate-snapshot.timer deskstate-shutdown.service deskstate-watch.service; do
  systemctl --user is-enabled --quiet "$unit" && pass "$unit enabled" || bad "$unit not enabled"
done
systemctl --user is-active --quiet deskstate-watch.service \
  && pass "reconcile watcher running" \
  || warn "deskstate-watch.service not running - workspace drift won't be corrected"
snapshot_state=$(python3 - <<'PY' 2>/dev/null
import json, os
s = json.load(open(os.path.expanduser('~/.local/state/deskstate/latest.json')))
w = (s.get('windows') or [{}])[0]
print('yes' if 'slot' in w and 'monitor_desc' in w else 'no')
PY
)
[[ $snapshot_state == yes ]] && pass "snapshot records workspace slot + monitor identity" \
  || warn "old snapshot format - run: deskstate snapshot"
systemctl --user is-active --quiet deskstate-snapshot.timer && pass "snapshot timer running" || bad "snapshot timer not running"
for bin in deskstate deskstate-preview deskstate-restore-window; do
  [[ -x $HOME/.local/bin/$bin ]] && pass "~/.local/bin/$bin executable" || bad "~/.local/bin/$bin missing or not executable"
done
ls "$HOME/.local/state/deskstate/latest.json" >/dev/null 2>&1 \
  && pass "a snapshot exists" || warn "no snapshot yet (waits for the next timer tick)"

step "appearance"
theme_now="$(cat "$HOME/.local/state/omarchy/current/theme.name" 2>/dev/null || true)"
theme_want="$(cat "$REPO_ROOT/state/omarchy/theme.name" 2>/dev/null || true)"
bg_now="$(readlink -f "$HOME/.local/state/omarchy/current/background" 2>/dev/null || true)"
bg_want="$(cat "$REPO_ROOT/state/omarchy/background" 2>/dev/null || true)"
font_now="$(omarchy font current 2>/dev/null || true)"
font_want="$(cat "$REPO_ROOT/state/omarchy/font" 2>/dev/null || true)"

[[ $theme_now == "$theme_want" ]] && pass "theme: $theme_now" \
  || bad "theme is '$theme_now', repo says '$theme_want'"
[[ -n $bg_want && $(basename "$bg_now") == "$(basename "$bg_want")" ]] \
  && pass "background: $(basename "$bg_now")" \
  || bad "background is '$(basename "$bg_now")', repo says '$(basename "$bg_want")'"
[[ $font_now == "$font_want" ]] && pass "font: $font_now" \
  || warn "font is '$font_now', repo says '$font_want'"
grep -qs 'opacity = "1 1"' "$HOME/.local/state/omarchy/toggles/hypr/window-opaque.lua" \
  && pass "opaque-window toggle present" \
  || warn "~/.local/state/omarchy/toggles/hypr/window-opaque.lua missing (windows go transparent again)"


step "config completeness"
if grep -q 'require("hypr.window-pin")' "$HOME/.config/hypr/hyprland.lua" 2>/dev/null; then
  [[ -f $HOME/.config/hypr/window-pin.lua ]] \
    && pass "window-pin.lua present (hyprland.lua requires it)" \
    || bad "hyprland.lua requires hypr.window-pin but the file is missing - Hyprland config will error"
fi

step "idle and power"
idle_json=$(omarchy-shell idle status 2>/dev/null || echo '{}')
saver=$(jq -r '.screensaver // empty' <<<"$idle_json")
lock=$(jq -r '.lock // empty' <<<"$idle_json")
blank=$(omarchy-shell lock status 2>/dev/null | jq -r '.blank // empty')
[[ $saver == "120" ]] && pass "screensaver after 2 minutes" || bad "screensaver is ${saver:-?}s, expected 120"
[[ $lock == "1200" ]] && pass "lock screen after 20 minutes" || bad "lock is ${lock:-?}s, expected 1200"
[[ $blank == "600" ]] && pass "panels off 10 minutes after the lock" \
  || warn "blank is ${blank:-?}s, expected 600 (is the local patch applied?)"
idle_action=$(busctl get-property org.freedesktop.login1 /org/freedesktop/login1 \
  org.freedesktop.login1.Manager IdleAction 2>/dev/null | awk -F'"' '{print $2}')
[[ $idle_action == "ignore" ]] && pass "no idle suspend (logind IdleAction=ignore)" \
  || bad "logind IdleAction=${idle_action:-?} - the machine can suspend when idle"
lid=$(busctl get-property org.freedesktop.login1 /org/freedesktop/login1 \
  org.freedesktop.login1.Manager HandleLidSwitch 2>/dev/null | awk -F'"' '{print $2}')
[[ $lid == "suspend" ]] && pass "lid close suspends (laptop)" || warn "HandleLidSwitch=${lid:-?}"
[[ -x $HOME/.local/bin/screen-power ]] && pass "screen-power present" || bad "~/.local/bin/screen-power missing"
$HOME/.local/bin/omarchy-patch-idle-blank --check >/dev/null 2>&1 \
  && pass "lock-screen patch applied" \
  || warn "lock-screen patch not applied - run omarchy-patch-idle-blank"
grep -q 'fullscreen({ window' "$HOME/.local/bin/deskstate" \
  && pass "deskstate restores fullscreen with action=set (SUPER + F survives)" \
  || warn "deskstate may not preserve Super+F fullscreen"

step "editor and audio"
[[ -f $HOME/.config/nvim/lazy-lock.json ]] && pass "nvim config + lazy-lock present" || bad "~/.config/nvim missing"
[[ -L $HOME/.config/nvim/lua/plugins/theme.lua ]] \
  && pass "nvim theme symlink -> $(readlink "$HOME/.config/nvim/lua/plugins/theme.lua")" \
  || warn "nvim theme.lua is not a symlink to the live Omarchy theme"
grep -rqs 'session.suspend-timeout-seconds = 0' "$HOME/.config/wireplumber/" \
  && pass "KEF LSX II LT never-suspend rule present" \
  || warn "wireplumber KEF rule missing — the USB speaker will drop after idle"
grep -qs 'x-scheme-handler/https=' "$HOME/.config/mimeapps.list" \
  && pass "default browser/url handlers set (mimeapps.list)" \
  || warn "~/.config/mimeapps.list missing (links may open in the wrong browser)"

step "vitals (system monitor)"
if pacman -Q vitals >/dev/null 2>&1; then
  pass "package: $(pacman -Q vitals)"
else
  bad "vitals not installed (run ./desk install vitals)"
fi
[[ -x /usr/bin/vitals ]] && pass "/usr/bin/vitals present" || bad "/usr/bin/vitals missing"
grep -q '^GenericName=System Monitor' <(cat "$HOME/.local/share/applications/vitals.desktop" /usr/share/applications/vitals.desktop 2>/dev/null) \
  && pass "desktop entry is searchable as 'System Monitor'" \
  || bad "vitals.desktop lost its GenericName (menu search will not find it)"
grep -q '"vitals"' "$HOME/.config/omarchy/extensions/omarchy-menu.jsonc" 2>/dev/null \
  && pass "System Monitor row present in omarchy-menu.jsonc" \
  || warn "no vitals row in omarchy-menu.jsonc (SUPER + SPACE -> System Monitor)"

step "VRAM sanity"
used=$(cat /sys/class/drm/card1/device/mem_info_vram_used 2>/dev/null || echo 0)
human=$(numfmt --to=iec <<<"$used" 2>/dev/null || echo '?')
if (( used < 12 * 1024 * 1024 * 1024 )); then
  pass "dGPU VRAM in use: $human (of 24G)"
else
  warn "dGPU VRAM in use: $human — see ai/HARDWARE.md#known-hardware-quirks; reboot reclaims a leaked pile"
fi

printf '\n'
(( fail )) && { printf 'Some checks failed.\n'; exit 1; }
printf 'All checks passed.\n'
