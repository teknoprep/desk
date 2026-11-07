-- window-pin: keep every window on the workspace and monitor it was on.
--
-- Omarchy gives every monitor its own block of ten workspaces and renumbers
-- them whenever a display comes or goes
-- (/usr/share/omarchy/default/hypr/monitor-workspaces.lua). When a monitor
-- blinks -- a display that drops its link when the screens power down -- that
-- reconcile can slide a workspace one slot to the right and leave the old
-- number behind, empty, with the windows stranded on the next desktop.
--
-- This remembers where each window lived, and after a display change (or a
-- config reload, which is how the reconcile runs) puts it back, as long as its
-- monitor and workspace still exist. A monitor that is gone keeps its windows
-- where Hyprland parked them and gets them back when it returns. Outside those
-- few seconds this does nothing, so windows go wherever you put them.
--
-- State lives in ~/.local/state/window-pin so a config reload does not lose
-- it. `hyprctl eval 'o.window_pin.pause()'` switches the guard off until
-- resume(), or until the next config reload.

local SETTLE_SECONDS = 12
local TICK_MS = 500
local RECORD_MS = 1000

local HOME = os.getenv("HOME") or "/tmp"
local STATE_DIR = (os.getenv("XDG_STATE_HOME") or (HOME .. "/.local/state"))
local STATE_FILE = STATE_DIR .. "/window-pin"
local LOG_FILE = STATE_DIR .. "/window-pin.log"

-- address -> { workspace = id, monitor = name }, kept on disk so a reload of
-- this config does not forget where things were a second ago.
local home = {}
local written = nil
local settling = false
local settle_ticks = 0
local paused = false

local function log(message)
  local file = io.open(LOG_FILE, "a")
  if not file then
    return
  end
  file:write(os.date("%Y-%m-%dT%H:%M:%S ") .. message .. "\n")
  file:close()
end

local function load()
  local file = io.open(STATE_FILE, "r")
  if not file then
    return
  end

  for line in file:lines() do
    local address, workspace, monitor, class = line:match("^([^\t]+)\t(%d+)\t([^\t]+)\t(.*)$")
    if address then
      home[address] = { workspace = tonumber(workspace), monitor = monitor, class = class }
    end
  end

  file:close()
end

local function save()
  local addresses = {}
  for address in pairs(home) do
    addresses[#addresses + 1] = address
  end
  table.sort(addresses)

  local lines = {}
  for _, address in ipairs(addresses) do
    local where = home[address]
    lines[#lines + 1] = address .. "\t" .. where.workspace .. "\t" .. where.monitor .. "\t" .. (where.class or "")
  end

  local content = table.concat(lines, "\n")
  if content == written then
    return
  end

  local file = io.open(STATE_FILE, "w")
  if not file then
    os.execute("mkdir -p " .. string.format("%q", STATE_DIR))
    file = io.open(STATE_FILE, "w")
  end

  if file then
    file:write(content)
    file:close()
    written = content
  end
end

-- Where a window is now, or nil for the ones we never touch: special
-- workspaces (scratchpad, screensaver), pinned windows, unmapped ones.
local function placement(window)
  local workspace = window.workspace
  local monitor = window.monitor
  if not workspace or not monitor or not workspace.id or workspace.id <= 0 then
    return nil
  end
  if not window.mapped or window.pinned then
    return nil
  end
  return { workspace = workspace.id, monitor = monitor.name, class = window.class }
end

local function windows()
  return hl.get_windows({ mapped = true })
end

local function remember()
  if settling or paused then
    return
  end

  local live = {}
  for _, window in ipairs(windows()) do
    local where = placement(window)
    if where then
      home[window.address] = where
      live[window.address] = true
    end
  end

  -- Windows that closed are forgotten; the rest of the map is untouched so a
  -- window that is briefly hidden keeps its home.
  local removed = false
  for address in pairs(home) do
    if not live[address] then
      home[address] = nil
      removed = true
    end
  end

  if removed or #windows() > 0 then
    save()
  end
end

local function restore()
  if paused then
    return
  end

  local monitors = {}
  for _, monitor in ipairs(hl.get_monitors()) do
    monitors[monitor.name] = monitor
  end

  for _, window in ipairs(windows()) do
    local where = home[window.address]
    local now = placement(window)

    if where and now and (now.workspace ~= where.workspace or now.monitor ~= where.monitor) then
      local target = hl.get_workspace(where.workspace)

      -- Only into a workspace that still exists, on the monitor it belongs to.
      -- A workspace whose monitor is away is left alone: its windows come back
      -- when the monitor returns, rather than being parked on another screen.
      if monitors[where.monitor] and target and target.monitor and target.monitor.name == where.monitor then
        hl.dispatch(hl.dsp.window.move({
          window = "address:" .. window.address,
          workspace = tostring(where.workspace),
          follow = false,
        }))
        log("restore " .. (where.class or "?") .. " ws" .. now.workspace .. "/" .. now.monitor
          .. " -> ws" .. where.workspace .. "/" .. where.monitor)
      end
    end
  end
end

local tick

local function settle()
  if not settling then
    return
  end

  restore()
  settle_ticks = settle_ticks - 1

  if settle_ticks <= 0 then
    settling = false
    remember()
    log("layout settled")
    return
  end

  hl.timer(tick, { type = "oneshot", timeout = TICK_MS })
end

tick = settle

-- Freeze the map as it was a moment ago and hold it while the compositor and
-- Omarchy's reconcile do their work.
local function changed(reason)
  if settling then
    return
  end

  settling = true
  settle_ticks = math.max(1, math.floor(SETTLE_SECONDS * 1000 / TICK_MS))
  log("layout changed: " .. reason .. ", holding for " .. SETTLE_SECONDS .. "s")
  hl.timer(tick, { type = "oneshot", timeout = TICK_MS })
end

local function record_loop()
  remember()
  hl.timer(record_loop, { type = "oneshot", timeout = RECORD_MS })
end

load()

hl.on("monitor.added", function() changed("monitor added") end)
hl.on("monitor.removed", function() changed("monitor removed") end)
hl.on("monitor.layout_changed", function() changed("layout changed") end)
hl.on("config.reloaded", function() changed("config reloaded") end)

hl.timer(record_loop, { type = "oneshot", timeout = RECORD_MS })

-- `hyprctl eval 'o.window_pin.pause()'` stops the guard without a config
-- reload; resume() starts it again and forgets the old placement map so a
-- window you moved by hand while paused keeps its new home.
local M = {
  home = home,
  pause = function()
    paused = true
    log("paused")
  end,
  resume = function()
    paused = false
    settling = false
    remember()
    log("resumed")
  end,
  status = function()
    local count = 0
    for _ in pairs(home) do count = count + 1 end
    return (paused and "paused" or "watching") .. ", " .. count .. " windows"
  end,
}

o.window_pin = M

return M
