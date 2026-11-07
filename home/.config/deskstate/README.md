# deskstate - desktop session snapshots

Records what is on the desktop once a minute so a reboot, a crash or a power
cut does not lose the layout.

- Command: `~/.local/bin/deskstate`
- State: `~/.local/state/deskstate/` (`latest.json`, `summary.txt`,
  `scrollback/`, `restore/`, `history/*.json.gz`, `reconcile.log`,
  `restore-apps.log`)
- Timer: `systemctl --user status deskstate-snapshot.timer` (every 60 s)
- Final snapshot before a clean shutdown: `deskstate-shutdown.service`
- Corrects workspace drift: `deskstate-watch.service`
- Keybinding: `SUPER + SHIFT + R` opens a terminal and restores the snapshot

## What a snapshot records

- monitors, workspaces, and every window: class, title, workspace, monitor,
  position, size, floating/maximised state, and the process command line
- every kitty instance (one per `~/.config` instance socket): each OS window,
  each tab, each window's cwd, foreground process and the visible screen text
- the pi session behind every terminal that is running pi (see below)
- tmux: sessions, windows, panes, pane cwd, running command, 120 lines of
  scrollback per pane
- the last `ssh` command per terminal, so it can be recalled after a restore

A full snapshot takes about 200 ms and 60 MB peak RSS.

## Restore

```
deskstate restore --dry-run        # show the plan, start nothing
deskstate restore                  # restore everything
deskstate restore --only kitty     # just terminals
deskstate restore --reconnect-ssh  # actually re-run ssh instead of leaving it
```

What it does:

- recreates each kitty OS window from a generated session file, one tab per
  saved tab, each tab started in its saved cwd - a tab that ran `pi` restarts
  `pi --session <id>`, a tab that ran `ssh` gets a plain shell in the local cwd
  (so Up-arrow recalls the ssh command), any other tab gets its shell
- recreates tmux sessions/windows/panes with their cwds, replays `pi` panes
- relaunches the other apps from their recorded command line and puts each
  window back on its workspace, and at its exact position and size if floating
- prints a hint per terminal: which command to press Up for

What it does not do:

- restore what a program itself shows: vim/less/etc. come back as a shell in
  the same directory. The visible screen of each terminal is saved under
  `scrollback/` if you need to look at what was there.
- restore browser tabs - Edge keeps its own session; the window is relaunched
  and Edge brings back what its own "continue where you left off" setting says.
- restore pipes, background jobs or half-typed input.

## pi session mapping

pi does not keep its session file open, so the file is identified by:

1. process start time - pi creates its session file within a second of
   starting, which fingerprints it exactly;
2. if that fails (`pi --resume` keeps the old file), the session whose file
   grew since the previous snapshot, when exactly one pi process and one
   session are unmatched;
3. otherwise the newest unclaimed session for the same cwd, flagged as a guess
   - restore prints a warning and `pi -r` lets you pick the right one.

A session file is never assigned to two terminals.

## Workspace drift: `reconcile` and `watch`

Workspace ids on this desktop are not stable. Omarchy gives every monitor a
block of ten workspaces (`1-10` on the first monitor, `11-20` on the second,
and so on, whatever their connectors are called here) and renumbers them when a monitor comes or
goes, and Hyprland hands the lowest free id to anything new. The visible
symptom is windows on the main monitor sliding from desktop 1 to 2, then 2 to
3, across logins and wake-ups.

So a snapshot does not store the workspace *id* as the truth. It stores:

- `slot` - which of the monitor's ten workspaces it was (`(id - 1) % 10 + 1`)
- `monitor` - the connector
- `monitor_desc` - make, model and serial, which survive a rename

`target_workspace()` turns those back into a live id by asking Omarchy's own
mapping (`~/.local/state/omarchy/monitor-workspaces`) which block that monitor
owns, then `block * 10 + slot`. Restore, and everything below, place windows
that way instead of replaying a stale id.

```
deskstate reconcile            # report windows that are on the wrong workspace
deskstate reconcile --apply    # move them back (logs to reconcile.log)
deskstate watch                # do it when the compositor - not you - moves things
```

`watch` runs as `deskstate-watch.service` (user unit, restarts itself). It
reconciles on two structural events only:

- a monitor was added or removed - Omarchy renumbers blocks, windows shift;
- two or more windows landed on the same workspace within a couple of seconds
  - that is a relocation, not a hand drag.

A single window moving is always left alone: that is you tidying up. Windows on
special workspaces are never touched. `reconcile` only acts when it can
identify a window unambiguously (class, then title, then nearest recorded
position), and it skips anything it cannot tell apart.

The post-boot hook runs `restore`, then `reconcile --apply` 45 s later, once
the outputs and the renumbering have settled.

## Recalling an ssh session

`~/.bashrc` now flushes each command to `~/.bash_history` as soon as the prompt
returns (`PROMPT_COMMAND="history -a; starship_precmd"`), so after a restore the
ssh command that was running is the newest history entry and Up-arrow recalls
it, even after a power cut.

## Optional: restore automatically at login

Enabled: `~/.config/omarchy/hooks/post-boot.d/deskstate-restore` runs
`deskstate restore` six seconds after the desktop comes up, then
`deskstate reconcile --apply` 45 seconds later. Its output is appended to
`~/.local/state/deskstate/restore-last.log`.

Delete that file to stop it - the desktop will then only be rebuilt on demand
with `SUPER + SHIFT + R`.

## If an app does not come back

A launch that fails is no longer silent: stderr from every relaunch goes to
`~/.local/state/deskstate/restore-apps.log`, and a window that has not mapped
after 45 s (60 s for a browser) is retried once through `uwsm-app --`, which
is how Omarchy launches applications itself. A cold boot with four outputs
coming up can take longer than the old 20 s timeout - that alone used to
report `vitals did not come back` for a window that appeared a moment later.

## Changing the cadence

`systemctl --user edit deskstate-snapshot.timer` and set `OnUnitActiveSec`
(e.g. `15s` for a tighter window after a crash). History is pruned to the last
1440 snapshots (~24 h at one per minute).
