#!/usr/bin/env bash
# Refresh this repo from the machine as it is right now.
#
#   ./scripts/capture.sh            # rewrite the tracked files + appearance state
#   ./scripts/capture.sh --dry-run  # just say what would change
#
# Only paths that are already tracked are refreshed, so this can never pull in
# a credential or a runtime directory by accident. Anything else that looks
# custom is listed at the end for a human to decide about.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
STATE_DIR="$REPO_ROOT/state/omarchy"
DRY_RUN=0
[[ ${1:-} == "--dry-run" ]] && DRY_RUN=1

say()  { printf '  %s\n' "$*"; }
step() { printf '\n== %s\n' "$*"; }

step "config files"
changed=0
missing=0
while IFS= read -r rel; do
  src="$HOME/${rel#home/}"
  dst="$REPO_ROOT/$rel"
  if [[ ! -e $src && ! -L $src ]]; then
    say "gone    $rel"
    missing=$((missing + 1))
    continue
  fi
  if [[ -f $src && ! -L $src ]] && cmp -s "$src" "$dst"; then
    continue
  fi
  if [[ -L $src && -L $dst ]] && [[ $(readlink "$src") == "$(readlink "$dst")" ]]; then
    continue
  fi
  say "updated $rel"
  changed=$((changed + 1))
  (( DRY_RUN )) || cp -a "$src" "$dst"
done < <(cd "$REPO_ROOT" && git ls-files home)

step "appearance"
mkdir -p "$STATE_DIR"

theme="$(cat "$HOME/.local/state/omarchy/current/theme.name" 2>/dev/null || true)"
bg_path="$(readlink -f "$HOME/.local/state/omarchy/current/background" 2>/dev/null || true)"
font="$(omarchy font current 2>/dev/null || true)"

if [[ -z $theme ]]; then
  say "no current theme recorded - skipped"
else
  say "theme      $theme"
  (( DRY_RUN )) || printf '%s\n' "$theme" >"$STATE_DIR/theme.name"
fi

theme_bg_dir="$HOME/.local/state/omarchy/current/theme/backgrounds"
theme_src_bg_dir="$HOME/.config/omarchy/themes/$theme/backgrounds"
if [[ -z $bg_path ]]; then
  say "no background recorded - skipped"
elif [[ -f $bg_path && ( $bg_path == "$theme_bg_dir"/* || $bg_path == "$theme_src_bg_dir"/* ) ]]; then
  # a background shipped with the theme: the file itself is already in home/
  name="$(basename "$bg_path")"
  say "background $theme/$name"
  (( DRY_RUN )) || printf '%s\n' "$name" >"$STATE_DIR/background"
elif [[ -f $bg_path ]]; then
  # a picture the user picked from elsewhere: carry the file too
  name="$(basename "$bg_path")"
  say "background user/$name (copied in)"
  (( DRY_RUN )) || {
    mkdir -p "$STATE_DIR/backgrounds/$theme"
    cp -a "$bg_path" "$STATE_DIR/backgrounds/$theme/$name"
    printf 'user/%s\n' "$name" >"$STATE_DIR/background"
  }
fi

if [[ -n $font ]]; then
  say "font       $font"
  (( DRY_RUN )) || printf '%s\n' "$font" >"$STATE_DIR/font"
fi

step "look toggles (state that changes how windows are drawn)"
mkdir -p "$REPO_ROOT/home/.local/state/omarchy/toggles/hypr"
while IFS= read -r -d '' f; do
  rel="home/.local/state/omarchy/toggles/hypr/$(basename "$f")"
  if [[ -f $REPO_ROOT/$rel ]] && cmp -s "$f" "$REPO_ROOT/$rel"; then
    continue
  fi
  say "updated $rel"
  (( DRY_RUN )) || cp -a "$f" "$REPO_ROOT/$rel"
done < <(find "$HOME/.local/state/omarchy/toggles/hypr" -maxdepth 1 -type f -print0 2>/dev/null)

step "not tracked (decide by hand)"
declare -A tracked=()
while IFS= read -r rel; do
  tracked["$rel"]=1
done < <(cd "$REPO_ROOT" && git ls-files home)

for d in "$HOME/.config/omarchy" "$HOME/.config/systemd/user"; do
  [[ -d $d ]] || continue
  while IFS= read -r -d '' f; do
    rel="home/${f#"$HOME"/}"
    [[ -n ${tracked[$rel]:-} ]] && continue
    case "$rel" in
      *"/themes/"*) continue ;;                  # huge and already tracked
      *.sample|*.lock|*.bak*) continue ;;
      */toggles/*) continue ;;                    # handled above
    esac
    say "untracked $rel"
  done < <(find "$d" -maxdepth 2 -type f -print0 2>/dev/null)
done

printf '\n%d file(s) refreshed. Review with: git status --short && git diff\n' "$changed"
exit 0
