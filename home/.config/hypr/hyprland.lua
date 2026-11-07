-- Learn how to configure Hyprland: https://wiki.hypr.land/Configuring/Start/

-- Omarchy's bootstrap keeps path setup out of this user config.
dofile((os.getenv("OMARCHY_PATH") or "/usr/share/omarchy") .. "/default/hypr/bootstrap.lua")

-- Disable all Omarchy default bindings. Add your own in hypr/bindings.lua.
-- omarchy_default_bindings = false
--
-- Or disable only bindings for Omarchy's preinstalled apps/web apps while
-- keeping core window-manager bindings:
-- omarchy_preinstalled_bindings = false

-- Load Omarchy defaults.
require("default.hypr.omarchy")

-- Put your personal overrides in these files. They're loaded after Omarchy's
-- defaults so package updates can improve the defaults without rewriting your
-- ~/.config/hypr files.
-- Monitors are not part of this kit: every desk has its own cables, order,
-- rotation and scale. Arrange yours with the Displays app (SUPER + SPACE ->
-- Setup -> Displays), which writes hypr/monitors.lua for this machine. The
-- require is guarded so a fresh install with no monitor file still loads.
pcall(require, "hypr.monitors")
require("hypr.input")
require("hypr.bindings")
require("hypr.looknfeel")
require("hypr.autostart")

-- Keep windows on the workspace and monitor they were on when a display comes
-- or goes, so Omarchy's per-monitor workspace renumbering cannot strand them
-- one desktop over. See the header of window-pin.lua to turn it off.
require("hypr.window-pin")

-- Toggle config flags dynamically.
require("default.hypr.toggles")

-- Add any other personal Hyprland configuration below.
-- o.window("qemu", { workspace = "5" })
