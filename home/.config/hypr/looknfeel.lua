-- Change the default Omarchy look'n'feel.

-- Tight gaps: only a few pixels of desktop showing around and between
-- windows (Omarchy defaults to 10 out / 5 in, which reads as a wide frame
-- of wallpaper on these wide screens).
hl.config({
  general = {
    gaps_in = 2,
    gaps_out = 2,

    -- The resize-on-border grab zone defaults to 8px past the border, sized
    -- for Omarchy's wider gaps. With 2px gaps it spilled onto the edge of
    -- the neighbouring window (scrollbars included), flipping the pointer to
    -- resize arrows over window content. 2px keeps it inside the seam.
    extend_border_grab_area = 2,
  },

  misc = {
    -- Apps asking for attention (a browser tab, a video page, a chat app)
    -- can't steal keyboard focus or drag the mouse pointer to themselves.
    focus_on_activate = false,
  },

  dwindle = {
    -- Where the pointer is decides the split, not the shape of the space:
    -- drop a dragged window on the bottom/top of another to stack it
    -- below/above, on the left/right edge to put it beside. New windows
    -- open toward the pointer the same way. Without this, Omarchy's
    -- force_split = 2 sends everything to the right on these wide screens.
    smart_split = true,
  },
})

-- Opt another application in to Omarchy's standard transparency.
-- Find its class with: hyprctl clients
-- o.transparent_window("my-app")
-- o.transparent_window("my-app", "0.9 0.85") -- Custom active/inactive opacity.

-- https://wiki.hypr.land/Configuring/Basics/Variables/#general
-- hl.config({
--   general = {
--     -- No gaps between windows or borders.
--     gaps_in = 0,
--     gaps_out = 0,
--     border_size = 0,
--
--     -- Change to niri-like side-scrolling layout.
--     layout = "scrolling",
--   },
-- })

-- https://wiki.hypr.land/Configuring/Basics/Variables/#decoration
-- hl.config({
--   decoration = {
--     -- Use round window corners.
--     rounding = 8,
--
--     -- Dim unfocused windows (0.0 = no dim, 1.0 = fully dimmed).
--     dim_inactive = true,
--     dim_strength = 0.15,
--   },
-- })

-- https://wiki.hypr.land/Configuring/Basics/Variables/#animations
-- hl.config({
--   animations = {
--     -- Disable all animations.
--     enabled = false,
--   },
-- })

-- https://wiki.hypr.land/Configuring/Basics/Variables/#layout
-- hl.config({
--   layout = {
--     -- Avoid overly wide single-window layouts on wide screens.
--     single_window_aspect_ratio = { 1, 1 },
--   },
-- })

-- https://wiki.hypr.land/Configuring/Layouts/Scrolling-Layout/
-- hl.config({
--   scrolling = {
--     -- See only one column per screen instead of two.
--     column_width = 0.97,
--   },
-- })

-- Keep colour management out of the KMS plane path (render:non_shader_cm = 0
-- instead of Omarchy's 3). A portrait monitor on the integrated GPU is driven by the AMD
-- iGPU, and with hardware CTM/LUT commits on that output, moving the pointer
-- made the panel flash red. The compositor's own frames were clean (verified by
-- frame-by-frame screencopy: 705 frames with the pointer over that monitor, no
-- colour anomaly), so the artifact was below the compositor. Converting in the
-- shader path fixes it; HDR on the other outputs still works.
hl.config({
  render = {
    non_shader_cm = 0,
  },
})
