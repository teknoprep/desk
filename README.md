# desk — an Omarchy desktop kit you pick from

One repo and one small Python CLI. Pull it down, run `./desk`, and choose what this
machine should have: a system monitor app, a desktop that rebuilds itself after a
reboot, windows that stay on their workspace when a display blinks, themes, terminal
and editor configs, the web-app launchers, the packages. Grab some, leave the rest.

Built and used daily on **Omarchy 4.5 / Hyprland 0.56** (Arch, AMD GPU). The CLI itself is plain
`python3` with no dependencies.

**Nothing here is specific to one piece of hardware.** No monitor layout, modes, rotation, scale or
GPU model: displays are arranged on each machine with the **Displays** app
(`nwg-displays`, in the menu at Setup → Displays), which writes `~/.config/hypr/monitors.lua` for
that machine. The kit installs the app and leaves the layout alone.

```console
$ git clone https://github.com/teknoprep/desk.git && cd desk
$ ./desk

desk — what should this machine have?

  1  vitals      missing    system monitor app (CPU, GPU, memory, disks, network, processes)
  2  deskstate   missing    snapshot the desktop every minute and rebuild it after a reboot
  3  window-pin  missing    windows stay on their workspace and monitor when a display blinks
  4  hyprland    missing    keybindings, gaps, input, autostart, window opacity (no monitor layout)
  5  displays    missing    the Displays app that owns this machine's monitor layout
  6  themes      missing    two generated themes, their backgrounds, and the look it was set to
  ...
 14  ai-apps     missing    settings for pi, claude and opencode, plus the superwhisper config
 15  packages    missing    the packages the config needs and stock Omarchy lacks (sudo)
 16  agent       ready      print the restore prompt to hand an AI agent instead of this picker

  * uses sudo · a = all · n = none · ?3 = details · q = quit
Pick [1-16, a, n, q]: 3,5,6
```

## The pieces

| # | Component | What it gives you | sudo |
|---|---|---|---|
| 1 | `vitals` | Qt Quick system monitor: CPU, GPU, memory, disks, network, busiest processes. Built from the bundled source and installed into `~/.local` |  |
| 2 | `deskstate` | A snapshot every minute of windows, terminals, tmux and scrollback, rebuilt after a reboot or power cut; `SUPER + SHIFT + R` to restore |  |
| 3 | `window-pin` | Hyprland Lua guard that puts windows back on their workspace and monitor after a display blinks, so nothing slides one desktop over |  |
| 4 | `hyprland` | Keybindings (`SUPER + wheel` resizes kitty's font), gaps, blur, input, autostart, opaque windows — **no monitor layout** |  |
| 5 | `displays` | Installs the **Displays** app (`nwg-displays`) and launches it: drag your monitors into place, resolution, scale and rotation. It writes the layout for this machine and nothing here overrides it | ✓ |
| 6 | `themes` | Two generated themes with 4K backgrounds, generators, and the theme/background/font the desk was set to |  |
| 7 | `shell` | Omarchy bar and menu settings, branding, and two extra menu rows (Displays, System Monitor) |  |
| 8 | `terminals` | kitty, alacritty, foot, ghostty, imv and the default-terminal list |  |
| 9 | `editor` | Neovim (LazyVim) with the theme hot-reload plugin and a pinned lockfile |  |
| 10 | `web-apps` | Launchers for Basecamp, Discord, the Google apps, HEY, WhatsApp, X, YouTube, Zoom |  |
| 11 | `idle-power` | Screensaver/lock/panel-off policy, the patch that makes panel-off actually work, no idle sleep | ✓ |
| 12 | `audio` | WirePlumber fixes: never suspend the KEF USB sink, Bluetooth A2DP autoconnect |  |
| 13 | `misc` | Shell rc, git/lazygit aliases, mimeapps, user dirs, XCompose, the share picker |  |
| 14 | `ai-apps` | Settings for pi, claude and opencode, and the Superwhisper dictation config |  |
| 15 | `packages` | The packages the configuration needs and stock Omarchy lacks (`packages/extras.txt`) | ✓ |
| 16 | `agent` | Prints `ai/RESTORE_PROMPT.md`: hand that to an AI agent and let it do the restore |  |

`./desk list` shows the same list with live status. `./desk ?3` shows exactly which
files a component would place and where.

## How it installs

- `home/…` is copied to your home directory, `system/…` to `/` (only `idle-power`).
- Files that already match are left alone; files that differ are **moved to
  `~/.local/state/desk/backup-<timestamp>/`** before being replaced, so any single
  piece can be rolled back by hand.
- Symlinks are preserved (Neovim's theme plugin links into the live Omarchy theme).
- Post steps run only where they make sense: `chmod`, `systemctl --user enable`,
  `hyprctl reload`, `omarchy theme/font set`, and for `vitals` a `qmake6 && make`
  build. Nothing is started or reloaded if you are not in the running session.

```bash
./desk install window-pin            # one piece, no questions asked? it asks once
./desk install all --yes             # everything
./desk install all --dry-run         # say what would happen, write nothing
./desk run vitals                    # launch an installed piece
./desk agent --copy                  # restore prompt on the clipboard
```

## Requirements

- **Omarchy 4.x** with the Lua Hyprland config (`~/.config/hypr/hyprland.lua`).
  The CLI refuses nothing, but the desktop pieces write that layout.
- `python3` (stdlib only) and `bash` for the CLI itself.
- `vitals` builds with `qmake6` + `make`: `base-devel qt6-base qt6-declarative qt6-wayland`.
- `packages` needs `sudo` and the network; it uses `yay` when present, `pacman` otherwise.

## Layout

```
desk                    the CLI: picker, installer, status, agent prompt
home/                   files that belong in $HOME (paths mirror the real home directory)
system/                 files that belong in /etc (only the logind drop-in)
state/omarchy/          what the desktop looks like: theme, background, font
apps/vitals/            the system monitor's source (own repo: teknoprep/vitals)
packages/               extras.txt (non-stock packages), explicit.txt (full package list)
ai/                     design decisions and the agent restore prompt
inventory.md            every repo path → its destination and why, one table per area
scripts/                install.sh (everything, no questions), capture.sh, verify.sh
```

## What is deliberately not in here

This is a public repo, so it carries configuration and code only — no secrets, no
machine identity, no captured session data.

| Left out | Why |
|---|---|
| `~/.ssh/*`, `~/.config/gh/hosts.yml`, rclone config, pi/opencode auth | credentials |
| `~/.local/state/**`, deskstate snapshots, clipboard history | runtime state, window titles, commands |
| `/etc/kernel/cmdline`, LUKS UUIDs | this disk's identity |
| Ollama models and the VRAM drop-in | tuned to one GPU and one model mix |
| Monitor modes, positions, rotation, scale | belongs to one desk's cables; use the Displays app |

Nothing in the repo is specific to one account: no personal name, email, hostname,
serial number or home path. Where a value has to be machine-specific (the GTK
bookmarks, the git identity) it is generated at install time or left for you to set.

## Licence

MIT for the scripts and configuration here (see `LICENSE`). Bundled and referenced
work keeps its own licence: `vitals` (MIT), LazyVim (Apache-2.0, in
`home/.config/nvim/LICENSE`).
