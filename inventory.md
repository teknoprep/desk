# Inventory — where every file goes

Table columns: repo path → destination on the machine → what it does.
Install with `./desk` (interactive: pick the pieces you want) or
`./scripts/install.sh` (everything); paths are applied verbatim.

## Hyprland

| Repo | Destination | Purpose |
|---|---|---|
| `home/.config/hypr/hyprland.lua` | `~/.config/hypr/hyprland.lua` | Omarchy bootstrap + includes; stock, kept so the include order is pinned |
| `home/.config/hypr/bindings.lua` | same | `SUPER + wheel` = kitty font size (and workspace scroll elsewhere), `deskstate` restore bind |
| `home/.config/hypr/input.lua` | same | input/touchpad/scroll settings |
| `home/.config/hypr/looknfeel.lua` | same | gaps, borders, blur, animations |
| `home/.config/hypr/autostart.lua` | same | exec-once entries |
| `home/.config/hypr/window-pin.lua` | same | keeps windows on their workspace/monitor across a display coming or going (see `ai/DECISIONS.md`) |

## Terminals

| Repo | Destination | Purpose |
|---|---|---|
| `home/.config/kitty/kitty.conf` | same | tab bar on top, `mouse_hide_wait 0`, Omarchy theme include |
| `home/.config/alacritty/alacritty.toml` | same | Alacritty config |
| `home/.config/foot/foot.ini` | same | foot config |

## Omarchy shell and menu

| Repo | Destination | Purpose |
|---|---|---|
| `home/.config/omarchy/extensions/omarchy-menu.jsonc` | same | adds **Setup → Displays (drag & drop)** → `nwg-displays`, and a root **System Monitor** row → `vitals` |
| `home/.config/omarchy/shell.json` | same | shell settings (bar layout, plugins) |
| `home/.config/omarchy/shell.toml` | same | shell theme tokens for the active theme |
| `home/.config/omarchy/branding/about.txt` | same | About window text |
| `home/.config/omarchy/branding/screensaver.txt` | same | screensaver text |
| `home/.config/omarchy/hooks/post-boot.d/deskstate-restore` | same | post-boot hook that reopens the deskstate snapshot after login |
| `home/.config/omarchy/hooks/theme-set.d/10-owe-sync` | same | theme-set hook |
| `home/.config/omarchy/defaults/agent` | same | which agent Omarchy's menu hands the terminal to (`pi`) |
| `home/.config/omarchy/defaults/dictation` | same | which dictation app the menu/HUD uses (`superwhisper`) |

## Themes (AI-generated)

| Repo | Destination | Purpose |
|---|---|---|
| `home/.config/omarchy/themes/machine-elf/**` | same | theme `machine-elf`: `colors.toml`, `shell.toml`, `icons.theme`, `preview.png`, 3 × 4K backgrounds, `make-backgrounds.sh` |
| `home/.config/omarchy/themes/elf-recursion/**` | same | theme `elf-recursion`: same layout, generator is `make-backgrounds.py` |

Activate with `omarchy theme set machine-elf` / `elf-recursion`. Regenerating the art is optional —
the backgrounds are committed.

## deskstate (desktop session snapshots)

| Repo | Destination | Purpose |
|---|---|---|
| `home/.local/bin/deskstate` | `~/.local/bin/deskstate` (executable) | snapshot/restore engine (~44 KB Python) |
| `home/.local/bin/deskstate-preview` | same | renders a preview image of the last snapshot |
| `home/.local/bin/deskstate-restore-window` | same | what `SUPER + SHIFT + R` runs in a terminal |
| `home/.config/deskstate/README.md` | same | full documentation |
| `home/.config/systemd/user/deskstate-snapshot.service` | same | one-shot snapshot unit |
| `home/.config/systemd/user/deskstate-snapshot.timer` | same | every 60 s, 30 s after startup |
| `home/.config/systemd/user/deskstate-shutdown.service` | same | final snapshot before the graphical session goes away |
| `home/.config/systemd/user/deskstate-watch.service` | same | `deskstate watch`: corrects workspace drift on monitor changes and grouped window relocations |

Runtime state lives in `~/.local/state/deskstate/` and is not tracked here.

## Other user units

| Repo | Destination | Purpose |
|---|---|---|
| `home/.config/systemd/user/rclone-onedrive.service` | same | mounts `onedrive:` on `~/OneDrive` (credentials are *not* included — run `rclone config`) |

## pi (agent harness)

| Repo | Destination | Purpose |
|---|---|---|
| `home/.pi/agent/settings.json` | same | theme + UI settings |

Not included, and not needed: `~/.pi/agent/skills/*` and `~/.config/omarchy/plugins/superwhisper-panel`
are **symlinks created by packages** (`/usr/share/omarchy/default/agents/skills/*` and
`/opt/superwhisper/assets/omarchy-plugin/*`). They reappear when you install Omarchy's agent skills
and `omarchy install dictation superwhisper`.

## Shell, apps, and other custom bits

| Repo | Destination | Purpose |
|---|---|---|
| `home/.bashrc` | `~/.bashrc` | Omarchy rc source plus the deskstate block: `histappend` + `PROMPT_COMMAND="history -a…"` so a restored terminal can recall the last command with Up-arrow |
| `home/.config/ghostty/config` | same | Ghostty: JetBrainsMono NF 9pt, theme include, padding 14, block cursor |
| `home/.config/git/config` | same | aliases, `pull.rebase`, `push.autoSetupRemote`, histogram diff |
| `home/.config/superwhisper/settings/settings.json` | same | dictation vocabulary + favourites (shortcuts/hypr blocks are generated from it) |
| `home/.local/share/applications/vitals.desktop` | same | searchable `Vitals` / *System Monitor* entry, mirroring the package's copy |


## Idle, lock and power

| Repo | Destination | Purpose |
|---|---|---|
| `home/.config/omarchy/shell.json` | same | `idle`: screensaver 120 s, lock 1200 s, blank 600 s (the last one needs the patch below) |
| `home/.local/bin/idle-settings` | same | the editor: `idle-settings` (gum TUI), `--show`, `--set lock=1200` |
| `home/.local/bin/screen-power` | same | turns the panels off/on through DDC brightness 0 and remembers the levels |
| `home/.local/bin/omarchy-patch-idle-blank` | same | patches Omarchy's lock service: `idle.blank` from shell.json, blank/wake through `screen-power` |
| `home/.config/omarchy/hooks/post-update.d/90-idle-blank-patch` | same | re-applies that patch after `omarchy update` (which replaces `/usr/share/omarchy`) |
| `system/etc/systemd/logind.conf.d/50-no-idle-sleep.conf` | `/etc/systemd/logind.conf.d/` | `IdleAction=ignore` (never suspend for idleness) and lid close → suspend on a laptop |

## Appearance — what the desktop actually looks like

`home/` alone is not enough: Omarchy keeps the *active* theme, the *active* background and the
font outside any config file. These three files are read by `desk`, which applies
them with `omarchy theme set`, `omarchy theme bg set` and `omarchy font set`.

| Repo | Destination | Purpose |
|---|---|---|
| `state/omarchy/theme.name` | applied, not copied | active theme: `elf-recursion` |
| `state/omarchy/background` | applied, not copied | active background inside that theme: `3-the-swarm.jpg` (a `user/…` value means the picture is carried in `state/omarchy/backgrounds/`) |
| `state/omarchy/font` | applied, not copied | active monospace font: `JetBrainsMono Nerd Font` |
| `home/.local/state/omarchy/toggles/hypr/{flags,window-opaque}.lua` | `~/.local/state/omarchy/toggles/hypr/` | window drawing toggles: `window-opaque.lua` pins opacity to `1 1` |

`scripts/capture.sh` rewrites these from a machine that already looks right, and refreshes every
tracked file at the same time — that is the one command to run before committing a new sync.

## Not carried: local LLMs

Ollama is set up per machine (VRAM reserve, KV cache type, context length, which models fit).
`~/.pi/agent/models.json` and the `ollama.service.d` drop-in are therefore **not** tracked, and
`desk` does not touch `ollama`.

## Not tracked (and why)

`~/.config/rclone/rclone.conf` (OAuth tokens), `~/.config/gh/hosts.yml`, `~/.ssh/`,
pi's auth/relay/model stores (credentials),
`/etc/default/limine` + `/etc/kernel/cmdline` (contain this disk's LUKS UUIDs),
`~/.local/state/**` (runtime), `~/.config/superwhisper/{shortcuts,hypr-block}.lua` (generated, and
`hypr-block.lua` hard-codes `$HOME`), and every
`*.bak.*` / `__pycache__`.

## Apps, editor, and desktop state (second sweep)

Everything here is hand-modified on this machine. Files that are byte-identical to
`/usr/share/omarchy/config/*` (`btop/btop.conf`, `starship.toml`, `tmux/tmux.conf`) are deliberately
**not** carried — `omarchy` owns them and its migrations keep them current.

| Repo | Destination | Purpose |
|---|---|---|
| `home/.config/nvim/**` | `~/.config/nvim/` | LazyVim with `editor.neo-tree` extra, `lazy-lock.json` pins, and the custom plugins `omarchy-theme-hotreload`, `all-themes`, `lualine-transparent`, `snacks-animated-scrolling-off`, plus `plugin/after/transparency.lua` and `lua/config/remote_clipboard.lua` |
| `home/.config/superwhisper/preferences.json` | same | dictation: Offline mode, `tone=semi-formal`, `cleanupGpuLayers=99`, Ctrl+Alt+Space toggle, launch at login |
| `home/.config/wireplumber/wireplumber.conf.d/kef-lsx-no-suspend.conf` | same | never suspend the KEF LSX II LT USB sink (its firmware wedges after idle and needs a replug) |
| `home/.config/wireplumber/wireplumber.conf.d/bluetooth-a2dp-autoconnect.conf` | same | auto-connect Bluetooth audio on A2DP |
| `home/.config/herdr/config.toml` | same | herdr mirrors the Omarchy tmux look (transparent tab bar, `new_cwd=follow`) |
| `home/.config/opencode/{opencode.json,cli.json}` | same | opencode config (`update=disable`) |
| `home/.config/mimeapps.list` | same | default apps: Edge for http/https/html, HEY for mailto, `superwhisper-url` handler |
| `home/.config/hyprland-mimeapps.list`, `~/.config/xdg-terminals.list`, `~/.config/user-dirs.dirs`, `~/.config/gtk-3.0/bookmarks` | same | desktop defaults and sidebar bookmarks |
| `home/.config/obsidian/user-flags.conf` | same | Obsidian flags |
| `home/.config/hyprland-preview-share-picker/config.yaml` | same | screenshot portal picker settings |
| `home/.config/xdg-desktop-portal/hyprland-portals.conf` | same | which portal answers which interface |
| `home/.config/nwg-displays/config` | same | the Displays app's own UI preferences (no layout: monitors are per machine) |
| `home/.config/hypr/{hyprsunset.conf,xdph.conf,.luarc.json}` | same | shipped by Omarchy but part of the Hyprland dir, kept so the whole directory round-trips |
| `home/.config/imv/config`, `home/.config/lazygit/config.yml`, `home/.config/gh/config.yml` | same | image viewer, lazygit, and gh preferences (no credentials in `config.yml`) |
| `home/.local/share/applications/*.desktop` | same | web-app launchers installed on this machine: Basecamp, Discord, Google {Contacts,Maps,Messages,Photos}, HEY, WhatsApp, X, YouTube, Zoom, plus the `Vitals` entry |
| `home/.pi/agent/themes/omarchy-system.json` | same | pi theme derived from the Omarchy palette |
| `home/.claude/themes/omarchy.json` | same | the same idea for Claude Code |
| `home/.XCompose` | same | `Multi-key n` → name, `Multi-key e` → email, plus Omarchy's emoji table |

Deliberately left out of this group: `~/.config/gh/hosts.yml`, `~/.config/rclone/rclone.conf`
(credentials), `~/.config/superwhisper/{cloud-device-id,cloud-usage.json,*.lock}`,
`~/.config/tmux/{tmux.conf}` / `starship.toml` / `btop/btop.conf` (stock Omarchy copies),
`~/.config/{ibus,fcitx,dconf,pulse,menus,mimeinfo.cache}` (runtime),
`~/.config/omarchy/**/*.sample` and `defaults/dictation.lock` (Omarchy-owned).
