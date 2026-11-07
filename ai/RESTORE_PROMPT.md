# Restore prompt for an AI agent

You are restoring Chris's customizations onto a machine that already runs a fresh **Omarchy 4.x**
install (Arch + Hyprland with the **Lua** config layout under `~/.config/hypr/*.lua`). Work through
this in order, verify each step, and stop and ask if something does not match.

Repository layout: `home/` mirrors `$HOME`, `system/` mirrors `/etc`, `packages/extras.txt` lists
non-stock packages, `ai/DECISIONS.md` explains the reasoning. **Monitors are not in this repo**: they
are arranged on the target machine with the Displays app.

## 0. Sanity check the target

```bash
omarchy --version            # 4.x, Lua config era
hyprctl version              # expect Hyprland 0.56+ (zwlr_output_manager_v1 support)
pacman -Q omarchy hyprland kitty
test -f ~/.config/hypr/hyprland.lua && echo "Lua config: OK"
```

If `~/.config/hypr/hyprland.lua` does not exist, this is an older Hyprland (`hyprland.conf`) era
machine: stop, the configs in this repo will not load.

## 1. Packages

```bash
omarchy pkg add nwg-displays jq grim imagemagick
```

Verify: `pacman -Q nwg-displays`.

Local LLMs are **not** part of this kit: those settings are tuned to one GPU and one VRAM budget.

## 2. Copy configuration files

Prefer the script, which backs up anything it overwrites:

```bash
././desk install all --yes      # dry-run: ./desk install all --dry-run
```

It copies `home/.config/hypr/*`, `home/.config/{kitty,alacritty,foot,ghostty}`,
`home/.config/omarchy/**` (both themes, branding, hooks, defaults, menu),
`home/.config/deskstate/`, `home/.config/systemd/user/deskstate-*` + `rclone-onedrive.service`,
`home/.config/superwhisper/settings.json`, `home/.config/git/config`, `home/.bashrc`,
`home/.local/bin/deskstate*`, `home/.local/share/applications/vitals.desktop`,
`home/.local/state/omarchy/toggles/hypr/*`, and `home/.pi/agent/settings.json`.

It also `chmod +x` on `~/.local/bin/deskstate*` and reloads Hyprland.

If you copy by hand, preserve modes: the three `deskstate` files must be executable.

## 3. Things the script cannot do (do these explicitly)

```bash
# deskstate: enable the snapshot timer + shutdown snapshot
systemctl --user daemon-reload
systemctl --user enable --now deskstate-snapshot.timer
systemctl --user enable deskstate-shutdown.service

# (no Ollama step - local LLMs are out of scope)
```

GitHub identity + credential helper (the helper must resolve through `PATH`, not a versioned path):

```bash
omarchy setup git      # name, email, gh auth login (choose HTTPS, do NOT pick a static gh path)
git config --global credential."https://github.com".helper '!gh auth git-credential'
```

OneDrive (unit shipped, credentials are not):

```bash
rclone config          # create a remote named "onedrive"
systemctl --user enable --now rclone-onedrive.service
```

Superwhisper dictation: install it with `omarchy install dictation superwhisper`; its bar panel and
agent skill are symlinks the package creates, and `~/.config/superwhisper/shortcuts.lua` +
`hypr-block.lua` are regenerated in-app. Only `settings.json` (vocabulary/favourites) ships here.

## 3a. The look: theme, background, font

`desk` already applies these from `state/omarchy/`, in the only order that works:

```bash
omarchy theme set "$(cat state/omarchy/theme.name)"                 # elf-recursion
omarchy theme bg set ~/.local/state/omarchy/current/theme/backgrounds/$(cat state/omarchy/background)
omarchy font set "$(cat state/omarchy/font)"
```

Do not skip this and expect the right picture: copying `home/.config/omarchy/themes/**` only makes
the themes *available*. Which theme is on, and which of its six backgrounds is showing, is runtime
state. If the background value starts with `user/`, the picture is carried in
`state/omarchy/backgrounds/<theme>/` and has to be copied to `~/.config/omarchy/backgrounds/<theme>/`
first.

## 3a-bis. Idle, lock and power

`desk` copies `shell.json` (screensaver 2 min, lock 20 min, blank 10 min), the logind drop-in
(`IdleAction=ignore`, lid suspends) and then runs `omarchy-patch-idle-blank`, restarting the shell.
Two things to check afterwards:

```bash
omarchy-shell idle status   # screensaver 120, lock 1200
omarchy-shell lock status   # blank 600
~/.local/bin/screen-power status   # every monitor on a DDC bus
```

The patch lives in `/usr/share/omarchy/shell/plugins/lock/Service.qml`, which an Omarchy update
replaces; `~/.config/omarchy/hooks/post-update.d/90-idle-blank-patch` re-applies it (and restarts
the shell). If Omarchy ever stops hardcoding the 5 s blank, drop the patch.

`screen-power` blanks by DDC brightness because Hyprland 0.56's `hl.dsp.dpms` is accepted and does
nothing — check `hyprctl monitors -j | jq '.[].dpmsStatus'` if a future version fixes it.

## 3b. `vitals`, the system monitor

The source is vendored in `apps/vitals/` (upstream: <https://github.com/teknoprep/vitals>):

```bash
./desk install vitals      # qmake6 + make, installs into ~/.local/bin
```

Then confirm it is reachable: `vitals` runs, and **SUPER + SPACE → System Monitor** exists (that row
lives in `home/.config/omarchy/extensions/omarchy-menu.jsonc`, already installed above).


## 4. Monitors — this one is yours

The kit deliberately carries **no** monitor layout: no modes, positions, scale, rotation or
connector rules. Every desk is different, and a copied layout is how you lose a screen.

Arrange them on the target machine with the Displays app:

```bash
nwg-displays &        # or SUPER + SPACE -> Setup -> Displays (drag & drop)
```

That writes `~/.config/hypr/monitors.lua`, which `hyprland.lua` loads (and skips when it is absent).
Nothing else in the kit depends on it. If a display misbehaves after the layout is applied, it is a
cable/port question for that machine, not a repo question.

## 5. Verify

```bash
./scripts/verify.sh
```

Expected: `hyprctl configerrors` empty, `SUPER + wheel` over kitty changes font size,
`systemctl --user is-active deskstate-snapshot.timer` = active, the theme is `elf-recursion` with
background `3-the-swarm.jpg`, and the font is `JetBrainsMono Nerd Font`. Monitors are whatever you
arranged in the Displays app — `verify.sh` only reports them, it does not expect a layout.

## 6. After a reboot

Run `./desk` again to see what is still missing, `./scripts/verify.sh` to prove the pieces that
matter are live, and arrange the displays once (they are saved per machine from then on).

