-- Keep only your personal keybinding overrides here. Add new bindings with
-- o.bind or replace defaults with o.rebind.

-- See current bindings and descriptions:
--   omarchy menu keybindings --print

-- To disable every Omarchy default binding, set this in
-- ~/.config/hypr/hyprland.lua before require("default.hypr.omarchy"), then add
-- only the bindings you want below:
--   omarchy_default_bindings = false

-- To disable all preinstalled app/webapp bindings, set:
--   omarchy_preinstalled_bindings = false

-- Add a new binding.
-- o.bind("SUPER + SHIFT + R", "SSH", "alacritty -e ssh your-server")

-- Change an existing binding. o.rebind takes the same arguments as o.bind.
-- This example replaces the default file manager with Flea.
-- o.rebind("SUPER + SHIFT + F", "File manager", { launch = "flea" })

-- Disable a default binding without replacing it.
-- hl.unbind("SUPER + SHIFT + B")

-- Logitech MX Keys examples:
-- o.bind("SUPER + H", nil, "voxtype record toggle")
-- o.bind("SUPER + PERIOD", nil, { panel = "omarchy.emojis" })

-- Restore the desktop recorded by deskstate (~/.local/bin/deskstate): kitty
-- tabs with their pi sessions and cwds, tmux panes, other app windows and
-- their monitors/workspaces. Snapshots are taken every minute by the
-- deskstate-snapshot systemd user timer, so this also survives a power cut.
o.bind("SUPER + SHIFT + R", "Restore desktop session", "kitty --title deskstate -e deskstate-restore-window")

-- SUPER + mouse wheel over kitty resizes its font, and keeps Omarchy's default
-- of scrolling through workspaces everywhere else. Kitty can't bind the wheel
-- itself (its mouse_map has no scroll buttons), so the wheel is caught here and
-- forwarded as kitty's own Ctrl+Shift+= / Ctrl+Shift+- shortcuts. Ctrl+Shift+=
-- still works as a keyboard-only alternative; Ctrl+Shift+BackSpace resets.
local function kitty_font_or_workspace(workspace, key)
  return function()
    local window = hl.get_active_window()
    local class = ((window and window.class) or ""):lower()

    if class:find("kitty", 1, true) then
      hl.dispatch(hl.dsp.send_key_state({ mods = "CTRL SHIFT", key = key, state = "down" }))

      hl.timer(function()
        hl.dispatch(hl.dsp.send_key_state({ mods = "CTRL SHIFT", key = key, state = "up" }))
      end, { timeout = 50, type = "oneshot" })
    else
      hl.dispatch(hl.dsp.focus({ workspace = workspace }))
    end
  end
end

o.rebind("SUPER + mouse_up", "Kitty font bigger / previous workspace", kitty_font_or_workspace("m-1", "equal"))
o.rebind("SUPER + mouse_down", "Kitty font smaller / next workspace", kitty_font_or_workspace("m+1", "minus"))
