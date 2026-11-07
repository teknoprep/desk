#!/usr/bin/env python3
"""Elf Recursion v2 - an 80s CRT that a machine elf is breaking out of.

A beige-box-era computer floats in hyperspace. Inside its green phosphor screen
a machine elf pushes both hands out through the glass at you, Videodrome style,
with two more elves peering over its shoulders. Inside *that* screen, behind
the elf, the whole scene repeats, and again, and again.

The recursion is rendered for real, outermost level last: each pass renders
the full canvas, then that image is cropped, barrel-distorted, scanlined and
bloomed like a CRT picture before becoming the screen of the next pass. Small
CRTs drift around the void showing the same scene, so every small elf carries
its own recursion inside it.

Usage: make-backgrounds.py <out.png> [--variant 1|2|3] [--depth N]
  variant 1  hero shot
  variant 2  pushed in on the screen and the hands
  variant 3  the swarm: the void full of elf CRTs
"""

import math
import os
import random
import subprocess
import sys
import tempfile

import cairo

# ------------------------------------------------------------------ canvas ---

W, H = 3840, 2160

# The stage is designed in its own coordinates and fitted into the canvas about
# the centre. Omarchy paints backgrounds PreserveAspectCrop, so this keeps the
# screen and the hands inside the band a 21:9 (and mostly a 32:9) panel keeps.
STAGE_SCALE = 0.82


def stage_to_canvas(x, y):
    return (W / 2 + (x - W / 2) * STAGE_SCALE, H / 2 + (y - H / 2) * STAGE_SCALE)


# Monitor, in stage coordinates. The screen is 4:3, as a CRT should be.
SW, SH = 1240.0, 930.0
SX, SY = 1920.0 - SW / 2, 430.0
SCX, SCY = SX + SW / 2, SY + SH / 2
MON_X0, MON_Y0 = SX - 150, SY - 125
MON_X1, MON_Y1 = SX + SW + 150, SY + SH + 215
BASE_Y0, BASE_Y1 = MON_Y1 + 12, MON_Y1 + 150
KB_Y0, KB_Y1 = BASE_Y1 + 28, BASE_Y1 + 168

TUNNEL_X, TUNNEL_Y = stage_to_canvas(SCX, SCY)

# What each screen shows of the level behind it: a 4:3 window over the full
# height of the canvas, so the small CRTs in the void are inside it too.
CROP_H = float(H)
CROP_W = CROP_H * 4 / 3
CROP_X0 = (W - CROP_W) / 2
CROP_Y0 = 0.0

# The elf inside the screen, and where its hands break the glass.
ELF_X, ELF_Y, ELF_U = SCX, 655.0, 440.0
HOLES = {-1: (SCX - 440, 1285.0), 1: (SCX + 440, 1285.0)}
WRISTS = {-1: (SCX - 515, 1290.0), 1: (SCX + 515, 1290.0)}
HAND_L = 530.0
HAND_TILT = 0.34
HOLE_R = 150.0


# ----------------------------------------------------------------- palette ---

def hx(s):
    s = s.lstrip("#")
    return tuple(int(s[i:i + 2], 16) / 255.0 for i in (0, 2, 4))


BG = hx("07050e")
VOID = hx("030209")
GREEN = hx("00ffa3")
GREEN_DK = hx("00b877")
CYAN = hx("2ee6ff")
VIOLET = hx("7a5cff")
MAGENTA = hx("ff2fd6")
GOLD = hx("ffb43d")
GOLD_LT = hx("ffdc8a")
GOLD_DK = hx("8a5a12")
RED = hx("ff3860")
WHITE = hx("e6fff5")
PUTTY = hx("2a251b")      # an 80s beige box, left in the dark
PUTTY_LT = hx("3d3526")
PUTTY_DK = hx("15120c")


def rgba(c, a):
    return (c[0], c[1], c[2], max(0.0, min(1.0, a)))


# ------------------------------------------------------------ path helpers ---

def rounded_rect(cr, x, y, w, h, r):
    r = min(r, abs(w) / 2, abs(h) / 2)
    cr.new_sub_path()
    cr.arc(x + w - r, y + r, r, -math.pi / 2, 0)
    cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi)
    cr.arc(x + r, y + r, r, math.pi, 3 * math.pi / 2)
    cr.close_path()


def crt_path(cr, x, y, w, h, r, bow):
    """A CRT face: rounded corners and every edge bowed slightly outward."""
    cr.new_path()
    cr.move_to(x + r, y)
    cr.curve_to(x + w * 0.35, y - bow, x + w * 0.65, y - bow, x + w - r, y)
    cr.curve_to(x + w - r * 0.45, y, x + w, y + r * 0.45, x + w, y + r)
    cr.curve_to(x + w + bow, y + h * 0.35, x + w + bow, y + h * 0.65, x + w, y + h - r)
    cr.curve_to(x + w, y + h - r * 0.45, x + w - r * 0.45, y + h, x + w - r, y + h)
    cr.curve_to(x + w * 0.65, y + h + bow, x + w * 0.35, y + h + bow, x + r, y + h)
    cr.curve_to(x + r * 0.45, y + h, x, y + h - r * 0.45, x, y + h - r)
    cr.curve_to(x - bow, y + h * 0.65, x - bow, y + h * 0.35, x, y + r)
    cr.curve_to(x, y + r * 0.45, x + r * 0.45, y, x + r, y)
    cr.close_path()


def screen_path(cr):
    crt_path(cr, SX, SY, SW, SH, 95, 16)


def cubic(p0, p1, p2, p3, n=24):
    out = []
    for i in range(n + 1):
        t = i / n
        m = 1 - t
        out.append((m ** 3 * p0[0] + 3 * m * m * t * p1[0] + 3 * m * t * t * p2[0] + t ** 3 * p3[0],
                    m ** 3 * p0[1] + 3 * m * m * t * p1[1] + 3 * m * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def catmull(points, n=10):
    """Smooth polyline through the given points."""
    pts = [points[0]] + list(points) + [points[-1]]
    out = []
    for i in range(1, len(pts) - 2):
        p0, p1, p2, p3 = pts[i - 1], pts[i], pts[i + 1], pts[i + 2]
        for k in range(n):
            t = k / n
            t2, t3 = t * t, t * t * t
            out.append(tuple(
                0.5 * ((2 * p1[j]) + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2
                       + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    out.append(points[-1])
    return out


def taper_path(cr, pts, w0, w1):
    """One closed ribbon along a polyline, its width tapering from w0 to w1."""
    left, right = [], []
    n = len(pts)
    for i, (x, y) in enumerate(pts):
        t = i / (n - 1.0)
        w = w0 + (w1 - w0) * t
        if i == 0:
            dx, dy = pts[1][0] - x, pts[1][1] - y
        elif i == n - 1:
            dx, dy = x - pts[-2][0], y - pts[-2][1]
        else:
            dx, dy = pts[i + 1][0] - pts[i - 1][0], pts[i + 1][1] - pts[i - 1][1]
        L = math.hypot(dx, dy) or 1.0
        nx, ny = -dy / L, dx / L
        left.append((x + nx * w / 2, y + ny * w / 2))
        right.append((x - nx * w / 2, y - ny * w / 2))
    cr.new_path()
    cr.move_to(*left[0])
    for p in left[1:]:
        cr.line_to(*p)
    for p in reversed(right):
        cr.line_to(*p)
    cr.close_path()


def membrane(cr, pathfn, u, rim=GREEN, glow=None, body=VOID, body_alpha=0.9,
             rim_w=3.0, rim_alpha=0.92, glow_scale=1.0, dissolve=None, tint=None):
    """A rim-lit shape: dark body, light bleeding in from its edge, crisp rim.

    dissolve = (y0, y1) fades the body and its glow out downward so a figure
    can melt back into the screen. tint is an optional pattern laid over the
    body with LIGHTEN, for iridescence.
    """
    glow = glow or rim
    cr.push_group()
    cr.save()
    pathfn(cr)
    cr.clip()
    cr.set_source_rgba(*rgba(body, body_alpha))
    cr.paint()
    if tint is not None:
        cr.set_operator(cairo.OPERATOR_LIGHTEN)
        cr.set_source(tint)
        cr.paint()
        cr.set_operator(cairo.OPERATOR_OVER)
    for w, a in ((0.11, 0.035), (0.07, 0.055), (0.04, 0.095), (0.022, 0.17), (0.010, 0.30)):
        pathfn(cr)
        cr.set_source_rgba(*rgba(glow, a))
        cr.set_line_width(w * u * glow_scale)
        cr.stroke()
    cr.restore()
    pathfn(cr)
    if isinstance(rim, cairo.Pattern):
        cr.set_source(rim)
    else:
        cr.set_source_rgba(*rgba(rim, rim_alpha))
    cr.set_line_width(rim_w)
    cr.stroke()
    pat = cr.pop_group()

    if dissolve is None:
        cr.set_source(pat)
        cr.paint()
    else:
        mask = cairo.LinearGradient(0, dissolve[0], 0, dissolve[1])
        mask.add_color_stop_rgba(0.0, 0, 0, 0, 1.0)
        mask.add_color_stop_rgba(0.6, 0, 0, 0, 0.45)
        mask.add_color_stop_rgba(1.0, 0, 0, 0, 0.0)
        cr.set_source(pat)
        cr.mask(mask)


# -------------------------------------------------------- 5x7 bitmap font ---

_GLYPHS = """
A .###. #...# #...# ##### #...# #...# #...#
B ####. #...# #...# ####. #...# #...# ####.
C .###. #...# #.... #.... #.... #...# .###.
D ####. #...# #...# #...# #...# #...# ####.
E ##### #.... #.... ####. #.... #.... #####
F ##### #.... #.... ####. #.... #.... #....
G .###. #...# #.... #.### #...# #...# .####
H #...# #...# #...# ##### #...# #...# #...#
I .###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.
J ..### ...#. ...#. ...#. ...#. #..#. .##..
K #...# #..#. #.#.. ##... #.#.. #..#. #...#
L #.... #.... #.... #.... #.... #.... #####
M #...# ##.## #.#.# #.#.# #...# #...# #...#
N #...# #...# ##..# #.#.# #..## #...# #...#
O .###. #...# #...# #...# #...# #...# .###.
P ####. #...# #...# ####. #.... #.... #....
Q .###. #...# #...# #...# #.#.# #..#. .##.#
R ####. #...# #...# ####. #.#.. #..#. #...#
S .###. #...# #.... .###. ....# #...# .###.
T ##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..
U #...# #...# #...# #...# #...# #...# .###.
V #...# #...# #...# #...# #...# .#.#. ..#..
W #...# #...# #...# #.#.# #.#.# #.#.# .#.#.
X #...# #...# .#.#. ..#.. .#.#. #...# #...#
Y #...# #...# .#.#. ..#.. ..#.. ..#.. ..#..
Z ##### ....# ...#. ..#.. .#... #.... #####
0 .###. #...# #..## #.#.# ##..# #...# .###.
1 ..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.
2 .###. #...# ....# ..##. .#... #.... #####
3 .###. #...# ....# ..##. ....# #...# .###.
4 ...#. ..##. .#.#. #..#. ##### ...#. ...#.
5 ##### #.... ####. ....# ....# #...# .###.
6 ..##. .#... #.... ####. #...# #...# .###.
7 ##### ....# ...#. ..#.. .#... .#... .#...
8 .###. #...# #...# .###. #...# #...# .###.
9 .###. #...# #...# .#### ....# ...#. .##..
. ..... ..... ..... ..... ..... .##.. .##..
, ..... ..... ..... ..... .##.. ..#.. .#...
: ..... .##.. .##.. ..... .##.. .##.. .....
" .#.#. .#.#. ..... ..... ..... ..... .....
' ..#.. ..#.. .#... ..... ..... ..... .....
* ..... ..#.. #.#.# .###. #.#.# ..#.. .....
] .###. ...#. ...#. ...#. ...#. ...#. .###.
[ .###. .#... .#... .#... .#... .#... .###.
( ...#. ..#.. .#... .#... .#... ..#.. ...#.
) .#... ..#.. ...#. ...#. ...#. ..#.. .#...
- ..... ..... ..... .###. ..... ..... .....
= ..... ..... ##### ..... ##### ..... .....
> .#... ..#.. ...#. ....# ...#. ..#.. .#...
/ ..... ....# ...#. ..#.. .#... #.... .....
_ ..... ..... ..... ..... ..... ..... #####
+ ..... ..#.. ..#.. ##### ..#.. ..#.. .....
! ..#.. ..#.. ..#.. ..#.. ..#.. ..... ..#..
? .###. #...# ....# ...#. ..#.. ..... ..#..
@ ##### ##### ##### ##### ##### ##### #####
"""
FONT = {" ": "." * 35}
for _line in _GLYPHS.strip().splitlines():
    _ch, *_rows = _line.split()
    assert len(_rows) == 7 and all(len(r) == 5 for r in _rows), _line
    FONT[_ch] = "".join(_rows)


def pixel_text(cr, lines, x, y, px, color, alpha=0.95, align="left", gap=0.82):
    """80s character-generator text: each lit cell is a square phosphor dot."""
    cell = 6 * px
    line_h = 9 * px
    cr.set_source_rgba(*rgba(color, alpha))
    for li, line in enumerate(lines):
        width = len(line) * cell
        lx = x - width / 2 if align == "center" else x
        for ci, ch in enumerate(line.upper()):
            glyph = FONT.get(ch, FONT["?"])
            glyph = glyph.ljust(35, ".")
            for r in range(7):
                for c in range(5):
                    if glyph[r * 5 + c] == "#":
                        cr.rectangle(lx + ci * cell + c * px, y + li * line_h + r * px, px * gap, px * gap)
    cr.fill()


# --------------------------------------------------------------------- elf ---

def head_path(cr, cx, cy, u):
    chin = (0.0, 0.400)
    segs = [
        ((0.040, 0.392), (0.078, 0.362), (0.096, 0.302)),
        ((0.120, 0.264), (0.136, 0.206), (0.144, 0.135)),
        ((0.149, 0.090), (0.152, 0.040), (0.152, -0.020)),
        ((0.152, -0.130), (0.135, -0.250), (0.082, -0.330)),
        ((0.054, -0.372), (0.025, -0.396), (0.0, -0.398)),
    ]
    P = lambda p: (cx + p[0] * u, cy + p[1] * u)
    pts, prev = [], chin
    for c1, c2, e in segs:
        pts.append((prev, c1, c2, e))
        prev = e
    cr.new_path()
    cr.move_to(*P(chin))
    for a, c1, c2, e in pts:
        cr.curve_to(*P(c1), *P(c2), *P(e))
    for a, c1, c2, e in reversed(pts):
        cr.curve_to(*P((-c2[0], c2[1])), *P((-c1[0], c1[1])), *P((-a[0], a[1])))
    cr.close_path()


def ear_path(cr, cx, cy, u, side):
    segs = [
        ((0.020, 0.090), (0.090, 0.135), (0.140, 0.128)),
        ((0.140, 0.128), (0.185, 0.070), (0.205, -0.020)),
        ((0.205, -0.020), (0.235, -0.150), (0.262, -0.330)),
        ((0.262, -0.330), (0.190, -0.250), (0.135, -0.170)),
        ((0.135, -0.170), (0.075, -0.110), (0.020, -0.060)),
    ]
    cr.new_path()
    cr.move_to(cx + side * 0.020 * u, cy + 0.090 * u)
    for c1, c2, e in segs:
        cr.curve_to(cx + side * c1[0] * u, cy + c1[1] * u, cx + side * c2[0] * u, cy + c2[1] * u,
                    cx + side * e[0] * u, cy + e[1] * u)
    cr.close_path()


def torso_path(cr, cx, cy, u):
    half = cubic((0, 0.615 * u), (0.10 * u, 0.655 * u), (0.215 * u, 0.695 * u), (0.315 * u, 0.775 * u), 18)
    half += cubic((0.315 * u, 0.775 * u), (0.285 * u, 0.845 * u), (0.235 * u, 0.865 * u), (0.225 * u, 0.955 * u), 14)
    half += cubic((0.225 * u, 0.955 * u), (0.265 * u, 1.14 * u), (0.255 * u, 1.34 * u), (0.265 * u, 1.55 * u), 14)
    pts = [(cx + dx, cy + dy) for dx, dy in half]
    cr.new_path()
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    for p in reversed(pts):
        cr.line_to(cx - (p[0] - cx), p[1])
    cr.close_path()


def eye(cr, cx, cy, w, h, rot, color=GREEN, bright=1.0):
    cr.save()
    cr.translate(cx, cy)
    cr.rotate(rot)
    cr.new_path()
    cr.move_to(-w * 0.58, 0)
    cr.curve_to(-w * 0.29, -h * 1.25, w * 0.29, -h * 1.25, w * 0.58, 0)
    cr.curve_to(w * 0.29, h * 1.25, -w * 0.29, h * 1.25, -w * 0.58, 0)
    cr.close_path()
    cr.set_source_rgba(*rgba(VOID, 0.95))
    cr.fill()
    cr.move_to(-w / 2, 0)
    cr.curve_to(-w / 4, -h, w / 4, -h, w / 2, 0)
    cr.curve_to(w / 4, h, -w / 4, h, -w / 2, 0)
    cr.close_path()
    cr.set_source_rgba(*rgba(color, 0.92 * bright))
    cr.fill()
    cr.move_to(0, -h * 0.80)
    cr.curve_to(-w * 0.045, -h * 0.30, -w * 0.045, h * 0.30, 0, h * 0.80)
    cr.curve_to(w * 0.045, h * 0.30, w * 0.045, -h * 0.30, 0, -h * 0.80)
    cr.close_path()
    cr.set_source_rgba(*rgba(VOID, 0.95))
    cr.fill()
    cr.set_source_rgba(*rgba(WHITE, 0.85 * bright))
    cr.arc(-w * 0.20, -h * 0.30, h * 0.20, 0, 2 * math.pi)
    cr.fill()
    cr.restore()
    g = cairo.RadialGradient(cx, cy, 1, cx, cy, w * 0.65)
    g.add_color_stop_rgba(0.0, *rgba(color, 0.32 * bright))
    g.add_color_stop_rgba(1.0, *rgba(color, 0.0))
    cr.set_source(g)
    cr.arc(cx, cy, w * 0.65, 0, 2 * math.pi)
    cr.fill()


def gold_diamond(cr, x, y, s, glow=MAGENTA):
    g = cairo.RadialGradient(x, y, 1, x, y, s * 4.5)
    g.add_color_stop_rgba(0.0, *rgba(glow, 0.55))
    g.add_color_stop_rgba(1.0, *rgba(glow, 0.0))
    cr.set_source(g)
    cr.arc(x, y, s * 4.5, 0, 2 * math.pi)
    cr.fill()
    cr.move_to(x, y - s * 1.7)
    cr.line_to(x + s, y)
    cr.line_to(x, y + s * 1.7)
    cr.line_to(x - s, y)
    cr.close_path()
    cr.set_source_rgba(*rgba(GOLD, 1.0))
    cr.fill_preserve()
    cr.set_source_rgba(*rgba(GOLD_LT, 1.0))
    cr.set_line_width(max(1.0, s * 0.25))
    cr.stroke()


def mandala(cr, cx, cy, u, strength=1.0):
    cols = [GREEN, GOLD, VIOLET, MAGENTA]
    for i, (r, a, lw) in enumerate(((0.52, 0.30, 3.0), (0.68, 0.22, 2.4), (0.86, 0.15, 2.0), (1.08, 0.10, 1.6))):
        cr.set_line_width(lw)
        cr.set_source_rgba(*rgba(cols[i % 4], a * strength))
        cr.arc(cx, cy, r * u, 0, 2 * math.pi)
        cr.stroke()
    cr.set_line_width(1.6)
    for i in range(48):
        th = i * 2 * math.pi / 48
        cr.set_source_rgba(*rgba(GOLD if i % 3 else MAGENTA, 0.22 * strength))
        cr.move_to(cx + math.cos(th) * 0.775 * u, cy + math.sin(th) * 0.775 * u)
        cr.line_to(cx + math.cos(th) * 0.825 * u, cy + math.sin(th) * 0.825 * u)
        cr.stroke()
    cr.set_line_width(2.0)
    for i in range(16):
        th = i * 2 * math.pi / 16
        a0, a1 = th - 0.13, th + 0.13
        cr.set_source_rgba(*rgba(GOLD if i % 2 else VIOLET, 0.12 * strength))
        cr.move_to(cx + math.cos(a0) * 0.94 * u, cy + math.sin(a0) * 0.94 * u)
        cr.curve_to(cx + math.cos(th) * 1.12 * u, cy + math.sin(th) * 1.12 * u,
                    cx + math.cos(th) * 1.12 * u, cy + math.sin(th) * 1.12 * u,
                    cx + math.cos(a1) * 0.94 * u, cy + math.sin(a1) * 0.94 * u)
        cr.stroke()


def elf_tint(cx, cy, u):
    g = cairo.LinearGradient(cx - 0.6 * u, cy - 0.6 * u, cx + 0.6 * u, cy + 2.0 * u)
    g.add_color_stop_rgba(0.00, *rgba(CYAN, 0.13))
    g.add_color_stop_rgba(0.30, *rgba(GREEN, 0.11))
    g.add_color_stop_rgba(0.60, *rgba(VIOLET, 0.10))
    g.add_color_stop_rgba(1.00, *rgba(GOLD, 0.08))
    return g


def elf(cr, cx, cy, u, rim=GREEN, body_alpha=0.6, bright=1.0, arms_to=None, halo=1.0):
    """A machine elf as phosphor: dark translucent body, light at the edges."""
    tint = elf_tint(cx, cy, u)
    if halo:
        mandala(cr, cx, cy, u, halo)
    membrane(cr, lambda c: taper_path(c, [(cx, cy + 0.40 * u), (cx, cy + 0.54 * u), (cx, cy + 0.68 * u)],
                                      0.20 * u, 0.36 * u),
             u, rim=rim, body_alpha=body_alpha, rim_w=2.6, glow_scale=0.7, tint=tint,
             dissolve=(cy + 0.50 * u, cy + 0.75 * u))
    membrane(cr, lambda c: torso_path(c, cx, cy, u), u, rim=rim, body_alpha=body_alpha, rim_w=2.8,
             glow_scale=0.7, tint=tint, dissolve=(cy + 0.75 * u, cy + 1.55 * u))
    if arms_to:
        for side, (hx_, hy_) in arms_to.items():
            sh = (cx + side * 0.29 * u, cy + 0.80 * u)
            el = (cx + side * 0.62 * u, cy + 1.02 * u)
            pts = cubic(sh, (cx + side * 0.48 * u, cy + 0.84 * u), el, (hx_, hy_), 30)
            membrane(cr, lambda c, p=pts: taper_path(c, p, 0.16 * u, 0.26 * u), u, rim=rim,
                     body_alpha=min(0.95, body_alpha + 0.2), rim_w=2.4, glow_scale=0.7, tint=tint)
    for side in (-1, 1):
        membrane(cr, lambda c, s=side: ear_path(c, cx, cy, u, s), u, rim=rim, body_alpha=0.95,
                 rim_w=2.8, glow_scale=0.30, tint=tint)
    membrane(cr, lambda c: head_path(c, cx, cy, u), u, rim=rim, body_alpha=0.96, rim_w=3.4,
             glow_scale=0.34, tint=tint)

    # face
    cr.save()
    cr.set_line_width(max(1.2, 0.0055 * u))
    cr.set_source_rgba(*rgba(rim, 0.13 * bright))
    for s in (-1, 1):
        cr.move_to(cx, cy - 0.398 * u)
        cr.curve_to(cx + s * 0.010 * u, cy - 0.250 * u, cx + s * 0.030 * u, cy - 0.150 * u, cx + s * 0.020 * u, cy - 0.010 * u)
        cr.stroke()
        cr.move_to(cx + s * 0.030 * u, cy - 0.250 * u)
        cr.curve_to(cx + s * 0.100 * u, cy - 0.210 * u, cx + s * 0.140 * u, cy - 0.130 * u, cx + s * 0.150 * u, cy - 0.030 * u)
        cr.stroke()
        cr.move_to(cx + s * 0.020 * u, cy + 0.150 * u)
        cr.curve_to(cx + s * 0.090 * u, cy + 0.180 * u, cx + s * 0.130 * u, cy + 0.240 * u, cx + s * 0.118 * u, cy + 0.300 * u)
        cr.stroke()
    cr.set_source_rgba(*rgba(rim, 0.34 * bright))
    cr.set_line_width(max(1.4, 0.0062 * u))
    for s in (-1, 1):
        cr.move_to(cx + s * 0.140 * u, cy + 0.020 * u)
        cr.curve_to(cx + s * 0.105 * u, cy - 0.030 * u, cx + s * 0.048 * u, cy - 0.038 * u, cx + s * 0.014 * u, cy - 0.010 * u)
        cr.stroke()
    cr.set_source_rgba(*rgba(rim, 0.26 * bright))
    cr.move_to(cx - 0.028 * u, cy + 0.268 * u)
    cr.line_to(cx + 0.028 * u, cy + 0.268 * u)
    cr.stroke()
    cr.restore()
    for s in (-1, 1):
        eye(cr, cx + s * 0.086 * u, cy + 0.058 * u, 0.178 * u, 0.048 * u, -s * 0.10, bright=bright)
    gold_diamond(cr, cx, cy - 0.105 * u, 0.013 * u)


# -------------------------------------------------------- the hands, outside ---

def hand_frame(wx, wy, side, L, tilt):
    ang = side * tilt
    ca, sa = math.cos(ang), math.sin(ang)

    def T(x, y):
        xs = side * x
        return (wx + L * (xs * ca - y * sa), wy + L * (xs * sa + y * ca))
    return T


def palm_path_fn(T):
    def f(cr):
        cr.new_path()
        cr.move_to(*T(-0.17, 0.02))
        cr.curve_to(*T(-0.05, 0.05), *T(0.07, 0.05), *T(0.17, 0.02))
        cr.curve_to(*T(0.26, -0.06), *T(0.31, -0.22), *T(0.31, -0.37))
        cr.curve_to(*T(0.31, -0.45), *T(0.30, -0.49), *T(0.28, -0.51))
        cr.curve_to(*T(0.10, -0.57), *T(-0.10, -0.57), *T(-0.27, -0.52))
        cr.curve_to(*T(-0.33, -0.45), *T(-0.37, -0.32), *T(-0.34, -0.21))
        cr.curve_to(*T(-0.30, -0.10), *T(-0.23, -0.02), *T(-0.17, 0.02))
        cr.close_path()
    return f


# base x, base y, angle (+ is outward), length, width, curl
FINGERS = [
    (-0.205, -0.50, -0.24, 0.62, 0.128, 0.13),   # index, nearest the face
    (-0.068, -0.535, -0.06, 0.70, 0.134, 0.07),  # middle
    (0.072, -0.525, 0.12, 0.66, 0.126, -0.06),   # ring
    (0.205, -0.48, 0.32, 0.50, 0.112, -0.13),    # little
]
THUMB = (-0.30, -0.21, -1.02, 0.46, 0.142, 0.22)


def finger_points(T, spec, segs=(0.42, 0.32, 0.26)):
    bx, by, a, length, width, curl = spec
    pts = [(bx, by)]
    x, y = bx, by
    for i, s in enumerate(segs[:3]):
        aa = a + curl * (i + 1)
        x += math.sin(aa) * length * s
        y -= math.cos(aa) * length * s
        pts.append((x, y))
    tip_a = a + curl * 4
    return pts, tip_a


def hand(cr, side, wx, wy, L, tilt, hole, solid=1.0):
    """A machine elf's hand coming at you through the glass, palm out."""
    T = hand_frame(wx, wy, side, L, tilt)
    u = L
    rim = cairo.LinearGradient(wx - side * L * 0.6, wy - L, wx + side * L * 0.6, wy + L * 0.2)
    rim.add_color_stop_rgba(0.0, *rgba(GOLD_LT, 0.95))
    rim.add_color_stop_rgba(0.55, *rgba(GOLD, 0.95))
    rim.add_color_stop_rgba(1.0, *rgba(GREEN, 0.9))
    tint = cairo.LinearGradient(wx, wy - L * 1.2, wx, wy + L * 0.3)
    tint.add_color_stop_rgba(0.0, *rgba(VIOLET, 0.16))
    tint.add_color_stop_rgba(0.5, *rgba(GREEN_DK, 0.10))
    tint.add_color_stop_rgba(1.0, *rgba(GOLD, 0.12))

    # forearm: from the hole in the glass to the wrist, foreshortened at you
    hx_, hy_ = hole
    fore = [(hx_, hy_), ((hx_ + wx) / 2, (hy_ + wy) / 2 + 6), T(0, 0.10)]
    membrane(cr, lambda c: taper_path(c, catmull(fore, 8), 0.34 * L, 0.40 * L), u, rim=rim,
             glow=GOLD, body_alpha=0.97, rim_w=3.2, glow_scale=0.55, tint=tint)
    # armour bands across the forearm
    cr.save()
    for t in (0.35, 0.7):
        px = hx_ + (wx - hx_) * t
        py = hy_ + (wy - hy_) * t
        dx, dy = wx - hx_, wy - hy_
        Ln = math.hypot(dx, dy) or 1
        nx, ny = -dy / Ln, dx / Ln
        half = (0.34 + 0.06 * t) * L / 2 * 0.92
        cr.move_to(px + nx * half, py + ny * half)
        cr.line_to(px - nx * half, py - ny * half)
        cr.set_source_rgba(*rgba(GOLD, 0.55))
        cr.set_line_width(3.0)
        cr.stroke()
    cr.restore()

    # thumb, behind the palm edge
    pts, ta = finger_points(T, THUMB, segs=(0.55, 0.45))
    world = [T(*p) for p in pts[:3]]
    membrane(cr, lambda c: taper_path(c, catmull(world, 8), THUMB[4] * L, THUMB[4] * L * 0.55), u,
             rim=rim, glow=GOLD, body_alpha=0.97, rim_w=2.8, glow_scale=0.4, tint=tint)
    claw(cr, world[-1], ta, T, THUMB[4] * L * 0.55, L, side)
    joints(cr, world[1:2], THUMB[4] * L * 0.75, along=[(world[0], world[2])])

    # palm
    membrane(cr, palm_path_fn(T), u, rim=rim, glow=GOLD, body_alpha=0.97, rim_w=3.4,
             glow_scale=0.5, tint=tint)
    # cuff at the wrist
    cr.save()
    a, b = T(-0.20, 0.03), T(0.20, 0.03)
    cr.move_to(*a)
    cr.curve_to(*T(-0.07, 0.10), *T(0.07, 0.10), *b)
    cr.set_source_rgba(*rgba(GOLD_LT, 0.85))
    cr.set_line_width(5)
    cr.stroke()
    cr.restore()

    # fingers
    for spec in FINGERS:
        pts, ta = finger_points(T, spec)
        world = [T(*p) for p in pts]
        w0 = spec[4] * L
        membrane(cr, lambda c, wp=world, ww=w0: taper_path(c, catmull(wp, 8), ww, ww * 0.52), u,
                 rim=rim, glow=GOLD, body_alpha=0.97, rim_w=2.6, glow_scale=0.36, tint=tint)
        joints(cr, world[1:3], w0 * 0.80, along=[(world[0], world[2]), (world[1], world[3])])
        claw(cr, world[-1], ta, T, w0 * 0.52, L, side)

    # knuckle studs
    for spec in FINGERS:
        x, y = T(spec[0], spec[1] + 0.02)
        cr.arc(x, y, L * 0.016, 0, 2 * math.pi)
        cr.set_source_rgba(*rgba(GOLD_LT, 0.9))
        cr.fill()

    # the sigil in the palm
    cx_, cy_ = T(-0.01, -0.27)
    cr.save()
    cr.translate(cx_, cy_)
    cr.rotate(side * tilt)
    s = L * 0.085
    cr.move_to(-s * 1.4, 0)
    cr.curve_to(-s * 0.6, -s * 0.9, s * 0.6, -s * 0.9, s * 1.4, 0)
    cr.curve_to(s * 0.6, s * 0.9, -s * 0.6, s * 0.9, -s * 1.4, 0)
    cr.close_path()
    cr.set_source_rgba(*rgba(GOLD, 0.85))
    cr.set_line_width(3.0)
    cr.stroke()
    for i in range(10):
        th = i * 2 * math.pi / 10
        cr.move_to(math.cos(th) * s * 1.65, math.sin(th) * s * 1.65)
        cr.line_to(math.cos(th) * s * 2.05, math.sin(th) * s * 2.05)
    cr.set_source_rgba(*rgba(GOLD, 0.55))
    cr.set_line_width(2.2)
    cr.stroke()
    cr.restore()
    gold_diamond(cr, cx_, cy_, L * 0.022)


def joints(cr, pts, width, along=None):
    """Gold knuckle bands across a finger, perpendicular to it."""
    for i, (x, y) in enumerate(pts):
        if along is not None:
            (ax, ay), (bx, by) = along[i]
            dx, dy = bx - ax, by - ay
        else:
            dx, dy = 0, 1
        n = math.hypot(dx, dy) or 1
        nx, ny = -dy / n, dx / n
        half = width * 0.47
        cr.move_to(x + nx * half, y + ny * half)
        cr.line_to(x - nx * half, y - ny * half)
        cr.set_source_rgba(*rgba(GOLD, 0.85))
        cr.set_line_width(max(2.0, width * 0.10))
        cr.stroke()


def claw(cr, base, local_angle, T, width, L, side):
    # direction of the claw in world space, from the local angle
    p0 = T(0, 0)
    p1 = T(math.sin(local_angle) * 0.1, -math.cos(local_angle) * 0.1)
    dx, dy = p1[0] - p0[0], p1[1] - p0[1]
    n = math.hypot(dx, dy) or 1
    dx, dy = dx / n, dy / n
    nx, ny = -dy, dx
    bx, by = base
    tipx, tipy = bx + dx * L * 0.13, by + dy * L * 0.13
    cr.move_to(bx + nx * width * 0.55, by + ny * width * 0.55)
    cr.curve_to(bx + nx * width * 0.5 + dx * L * 0.06, by + ny * width * 0.5 + dy * L * 0.06,
                tipx + nx * width * 0.15, tipy + ny * width * 0.15, tipx, tipy)
    cr.curve_to(tipx - nx * width * 0.1, tipy - ny * width * 0.1,
                bx - nx * width * 0.5 + dx * L * 0.05, by - ny * width * 0.5 + dy * L * 0.05,
                bx - nx * width * 0.55, by - ny * width * 0.55)
    cr.close_path()
    g = cairo.LinearGradient(bx, by, tipx, tipy)
    g.add_color_stop_rgba(0.0, *rgba(GOLD_DK, 1.0))
    g.add_color_stop_rgba(0.6, *rgba(GOLD, 1.0))
    g.add_color_stop_rgba(1.0, *rgba(GOLD_LT, 1.0))
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgba(*rgba(GOLD_LT, 0.9))
    cr.set_line_width(1.6)
    cr.stroke()


# ------------------------------------------------------------ broken glass ---

def jagged_ring(rng, cx, cy, r, n=17, jitter=0.28):
    pts = []
    for i in range(n):
        th = i * 2 * math.pi / n + rng.uniform(-0.12, 0.12)
        rr = r * rng.uniform(1 - jitter, 1 + jitter)
        pts.append((cx + math.cos(th) * rr, cy + math.sin(th) * rr))
    return pts


def cracks(cr, rng, cx, cy):
    """Radial fractures from the impact, plus broken concentric rings."""
    lines = []

    def walk(x, y, th, length, depth):
        pts = [(x, y)]
        travelled = 0
        while travelled < length:
            step = rng.uniform(16, 38)
            th += rng.uniform(-0.32, 0.32)
            x += math.cos(th) * step
            y += math.sin(th) * step
            travelled += step
            pts.append((x, y))
            if depth < 2 and rng.random() < 0.10:
                walk(x, y, th + rng.choice((-1, 1)) * rng.uniform(0.4, 0.9),
                     (length - travelled) * rng.uniform(0.3, 0.7), depth + 1)
        lines.append((pts, depth))

    n = 13
    for i in range(n):
        th = i * 2 * math.pi / n + rng.uniform(-0.15, 0.15)
        r0 = HOLE_R * rng.uniform(0.85, 1.1)
        walk(cx + math.cos(th) * r0, cy + math.sin(th) * r0, th, rng.uniform(120, 400), 0)

    for (pts, depth) in lines:
        for w, a, col in ((5.0, 0.55, VOID), (2.0, 0.65 - depth * 0.15, WHITE), (1.0, 0.5, GREEN)):
            cr.move_to(*pts[0])
            for p in pts[1:]:
                cr.line_to(*p)
            cr.set_source_rgba(*rgba(col, a))
            cr.set_line_width(w)
            cr.stroke()

    for rr, frac in ((HOLE_R * 1.30, 0.75), (HOLE_R * 1.75, 0.5), (HOLE_R * 2.3, 0.3)):
        ring = jagged_ring(rng, cx, cy, rr, n=28, jitter=0.10)
        for i in range(len(ring)):
            if rng.random() > frac:
                continue
            a, b = ring[i], ring[(i + 1) % len(ring)]
            cr.move_to(*a)
            cr.line_to(*b)
            cr.set_source_rgba(*rgba(WHITE, 0.40))
            cr.set_line_width(1.6)
            cr.stroke()


def hole(cr, rng, cx, cy):
    pts = jagged_ring(rng, cx, cy, HOLE_R, n=19, jitter=0.30)
    cr.move_to(*pts[0])
    for p in pts[1:]:
        cr.line_to(*p)
    cr.close_path()
    cr.set_source_rgba(*rgba(VOID, 0.62))
    cr.fill_preserve()
    cr.set_source_rgba(*rgba(GOLD_LT, 0.9))
    cr.set_line_width(3.5)
    cr.stroke()
    # bevelled glass edge
    inner = [(cx + (x - cx) * 1.12, cy + (y - cy) * 1.12) for x, y in pts]
    cr.move_to(*inner[0])
    for p in inner[1:]:
        cr.line_to(*p)
    cr.close_path()
    cr.set_source_rgba(*rgba(WHITE, 0.35))
    cr.set_line_width(1.5)
    cr.stroke()


def make_shards(rng, cx, cy, side, count=38):
    shards = []
    for _ in range(count):
        th = rng.uniform(0, 2 * math.pi)
        # bias outward and toward the viewer's side of this hand
        if rng.random() < 0.5:
            th = math.atan2(rng.uniform(-0.6, 1.0), side * rng.uniform(0.2, 1.0))
        d = HOLE_R * 1.05 + (rng.random() ** 0.8) * 640
        size = 9 + d * 0.055 * rng.uniform(0.5, 1.5)
        x, y = cx + math.cos(th) * d, cy + math.sin(th) * d
        nv = rng.choice((3, 3, 4))
        verts = []
        rot = rng.uniform(0, 2 * math.pi)
        for k in range(nv):
            a = rot + k * 2 * math.pi / nv + rng.uniform(-0.4, 0.4)
            r = size * rng.uniform(0.45, 1.25)
            verts.append((x + math.cos(a) * r, y + math.sin(a) * r * rng.uniform(0.4, 1.0)))
        edge = rng.choice((WHITE, GOLD_LT, GREEN, GOLD, CYAN))
        shards.append((d, verts, edge, rng.uniform(0.55, 0.95)))
    return shards


def draw_shards(cr, shards):
    for d, verts, edge, a in shards:
        cr.move_to(*verts[0])
        for v in verts[1:]:
            cr.line_to(*v)
        cr.close_path()
        xs = [v[0] for v in verts]
        ys = [v[1] for v in verts]
        g = cairo.LinearGradient(min(xs), min(ys), max(xs), max(ys))
        g.add_color_stop_rgba(0.0, *rgba(edge, 0.30 * a))
        g.add_color_stop_rgba(1.0, *rgba(VOID, 0.55 * a))
        cr.set_source(g)
        cr.fill_preserve()
        cr.set_source_rgba(*rgba(edge, 0.9 * a))
        cr.set_line_width(1.8)
        cr.stroke()
        vx, vy = verts[0]
        cr.arc(vx, vy, 2.4, 0, 2 * math.pi)
        cr.set_source_rgba(*rgba(WHITE, 0.9 * a))
        cr.fill()


# --------------------------------------------------------------- hyperspace ---

def backdrop(cr, rng, variant):
    cr.set_source_rgb(*BG)
    cr.paint()
    tx, ty = TUNNEL_X, TUNNEL_Y

    # A vector-graphics tunnel of CRT-shaped frames, Tempest style.
    cols = [GREEN, GOLD, VIOLET, MAGENTA, CYAN]
    frames = 24
    for k in range(frames):
        w = 260 * 1.17 ** k
        h = w * 0.75
        f = k / (frames - 1)
        cr.set_line_width(1.5 + 5 * f)
        cr.set_source_rgba(*rgba(cols[k % len(cols)], 0.05 + 0.14 * math.sin(math.pi * min(1, f * 1.2))))
        crt_path(cr, tx - w / 2, ty - h / 2, w, h, w * 0.08, w * 0.012)
        cr.stroke()

    # rails running down the tunnel from the frame corners and edges
    for i in range(20):
        th = i * 2 * math.pi / 20
        cr.move_to(tx + math.cos(th) * 120, ty + math.sin(th) * 90)
        cr.line_to(tx + math.cos(th) * 4200, ty + math.sin(th) * 3150)
        cr.set_source_rgba(*rgba(GOLD if i % 2 else GREEN, 0.06))
        cr.set_line_width(2.0)
        cr.stroke()

    # starfield, streaking out of the tunnel
    srng = random.Random(7)
    for _ in range(520):
        th = srng.uniform(0, 2 * math.pi)
        d = 200 + srng.random() ** 0.6 * 2600
        x, y = tx + math.cos(th) * d, ty + math.sin(th) * d * 0.75
        streak = d * 0.02 * srng.uniform(0.3, 1.6)
        col = srng.choice((WHITE, GOLD_LT, GREEN, CYAN, MAGENTA))
        cr.move_to(x, y)
        cr.line_to(x + math.cos(th) * streak, y + math.sin(th) * streak * 0.75)
        cr.set_source_rgba(*rgba(col, srng.uniform(0.25, 0.75)))
        cr.set_line_width(srng.uniform(1.2, 3.2))
        cr.stroke()

    # glow pool behind the computer: green core, gold and violet halo
    g = cairo.RadialGradient(tx, ty, 50, tx, ty, 2100)
    g.add_color_stop_rgba(0.0, *rgba(GREEN, 0.20))
    g.add_color_stop_rgba(0.22, *rgba(GOLD, 0.08))
    g.add_color_stop_rgba(0.5, *rgba(VIOLET, 0.07))
    g.add_color_stop_rgba(1.0, *rgba(VOID, 0.0))
    cr.set_source(g)
    cr.paint()


def paint_crop(cr, prev, x, y, w, h, alpha=1.0):
    """Paint the 4:3 recursion window of the previous level into a rect."""
    if prev is None:
        return
    cr.save()
    cr.rectangle(x, y, w, h)
    cr.clip()
    cr.translate(x, y)
    cr.scale(w / CROP_W, h / CROP_H)
    cr.translate(-CROP_X0, -CROP_Y0)
    cr.set_source_surface(prev, 0, 0)
    cr.get_source().set_filter(cairo.FILTER_GOOD)
    cr.paint_with_alpha(alpha)
    cr.restore()


def pod(cr, prev, cx, cy, w, rot, alpha=1.0):
    """A small 80s monitor adrift in hyperspace, showing the whole scene."""
    h = w * 0.86
    sw = w * 0.80
    sh = sw * 0.75
    sx, sy = -sw / 2, -h / 2 + w * 0.07
    cr.save()
    cr.translate(cx, cy)
    cr.rotate(rot)

    g = cairo.RadialGradient(0, 0, w * 0.2, 0, 0, w * 1.0)
    g.add_color_stop_rgba(0.0, *rgba(GOLD, 0.16 * alpha))
    g.add_color_stop_rgba(0.5, *rgba(VIOLET, 0.07 * alpha))
    g.add_color_stop_rgba(1.0, *rgba(VIOLET, 0.0))
    cr.set_source(g)
    cr.arc(0, 0, w * 1.0, 0, 2 * math.pi)
    cr.fill()

    # case, with a sliver of its top in perspective
    cr.move_to(-w / 2 + w * 0.04, -h / 2)
    cr.line_to(-w / 2 + w * 0.12, -h / 2 - w * 0.06)
    cr.line_to(w / 2 - w * 0.12, -h / 2 - w * 0.06)
    cr.line_to(w / 2 - w * 0.04, -h / 2)
    cr.close_path()
    cr.set_source_rgba(*rgba(PUTTY_LT, alpha))
    cr.fill()
    rounded_rect(cr, -w / 2, -h / 2, w, h, w * 0.05)
    cr.set_source_rgba(*rgba(PUTTY, alpha))
    cr.fill_preserve()
    cr.set_source_rgba(*rgba(GOLD, 0.75 * alpha))
    cr.set_line_width(max(1.5, w * 0.007))
    cr.stroke()

    cr.push_group()
    crt_path(cr, sx, sy, sw, sh, sw * 0.08, sw * 0.012)
    cr.clip()
    cr.set_source_rgb(*VOID)
    cr.paint()
    paint_crop(cr, prev, sx - sw * 0.02, sy - sh * 0.02, sw * 1.04, sh * 1.04, 0.95)
    # scanlines
    cr.set_source_rgba(0, 0, 0, 0.30)
    yy = sy
    step = max(2.0, sh / 90)
    while yy < sy + sh:
        cr.rectangle(sx, yy, sw, step * 0.45)
        yy += step
    cr.fill()
    gl = cairo.RadialGradient(0, sy + sh / 2, sh * 0.2, 0, sy + sh / 2, sw * 0.7)
    gl.add_color_stop_rgba(0.0, 0, 0, 0, 0)
    gl.add_color_stop_rgba(1.0, 0, 0, 0, 0.55)
    cr.set_source(gl)
    cr.paint()
    hl = cairo.LinearGradient(sx, sy, sx + sw * 0.4, sy + sh * 0.5)
    hl.add_color_stop_rgba(0.0, 1, 1, 1, 0.10)
    hl.add_color_stop_rgba(1.0, 1, 1, 1, 0.0)
    cr.set_source(hl)
    cr.paint()
    cr.pop_group_to_source()
    cr.paint_with_alpha(alpha)

    crt_path(cr, sx, sy, sw, sh, sw * 0.08, sw * 0.012)
    cr.set_source_rgba(*rgba(GREEN, 0.55 * alpha))
    cr.set_line_width(max(1.2, w * 0.004))
    cr.stroke()

    # badge strip: gold maker's plate and a green LED
    by = sy + sh + (h / 2 - (sy + sh)) * 0.5
    cr.rectangle(-w * 0.30, by - w * 0.012, w * 0.22, w * 0.024)
    cr.set_source_rgba(*rgba(GOLD, 0.8 * alpha))
    cr.fill()
    cr.arc(w * 0.36, by, w * 0.014, 0, 2 * math.pi)
    cr.set_source_rgba(*rgba(GREEN, alpha))
    cr.fill()
    cr.restore()


def pod_layout(variant):
    # (x, y, width, rotation, alpha) in canvas coordinates. Kept inside the
    # recursion window (x 480..3360) so each screen shows them too.
    base = [
        (860, 600, 400, -0.10, 0.95), (640, 1110, 300, 0.07, 0.85), (900, 1600, 340, -0.05, 0.9),
        (2980, 600, 400, 0.10, 0.95), (3200, 1110, 300, -0.07, 0.85), (2940, 1600, 340, 0.05, 0.9),
    ]
    if variant != 3:
        return base
    # the swarm: monitors packed around the computer without touching it or
    # each other, bigger the further out they drift
    rng = random.Random(23)
    keep_out = (1120, 300, 2720, 1820)
    pods = []
    for _ in range(20000):
        if len(pods) >= 30:
            break
        x = rng.uniform(560, 3280)
        y = rng.uniform(140, 2020)
        d = math.hypot((x - TUNNEL_X) / 1.4, y - TUNNEL_Y)
        w = (90 + min(1.0, d / 1100) * 240) * rng.uniform(0.7, 1.1)
        h = w * 0.92
        if x - w / 2 < 520 or x + w / 2 > 3320 or y - h / 2 < 60 or y + h / 2 > 2100:
            continue
        if (x + w / 2 > keep_out[0] and x - w / 2 < keep_out[2]
                and y + h / 2 > keep_out[1] and y - h / 2 < keep_out[3]):
            continue
        if any(math.hypot(x - px, y - py) < (w + pw) * 0.56 for px, py, pw, _, _ in pods):
            continue
        pods.append((x, y, w, rng.uniform(-0.16, 0.16), 0.6 + 0.35 * min(1.0, d / 1300)))
    pods.sort(key=lambda p: p[2])
    return pods


# ------------------------------------------------------------- the computer ---

def monitor(cr, screen_tex, res):
    # glow spilling off the screen onto the case
    g = cairo.RadialGradient(SCX, SCY, 200, SCX, SCY, 1300)
    g.add_color_stop_rgba(0.0, *rgba(GREEN, 0.16))
    g.add_color_stop_rgba(1.0, *rgba(GREEN, 0.0))
    cr.set_source(g)
    cr.arc(SCX, SCY, 1300, 0, 2 * math.pi)
    cr.fill()

    # top of the case, in perspective, with vents
    tl, tr = (MON_X0 + 40, MON_Y0 + 8), (MON_X1 - 40, MON_Y0 + 8)
    bl, br = (MON_X0 + 170, MON_Y0 - 92), (MON_X1 - 170, MON_Y0 - 92)
    cr.move_to(*tl)
    cr.line_to(*bl)
    cr.line_to(*br)
    cr.line_to(*tr)
    cr.close_path()
    tg = cairo.LinearGradient(0, MON_Y0 - 92, 0, MON_Y0)
    tg.add_color_stop_rgb(0.0, *PUTTY_DK)
    tg.add_color_stop_rgb(1.0, *PUTTY_LT)
    cr.set_source(tg)
    cr.fill_preserve()
    cr.set_source_rgba(*rgba(GOLD, 0.35))
    cr.set_line_width(2)
    cr.stroke()
    for i in range(16):
        f = (i + 0.5) / 16
        x0 = bl[0] + (br[0] - bl[0]) * (0.2 + 0.6 * f)
        x1 = tl[0] + (tr[0] - tl[0]) * (0.2 + 0.6 * f)
        cr.move_to(x0, MON_Y0 - 70)
        cr.line_to(x0 + (x1 - x0) * 0.6, MON_Y0 - 22)
    cr.set_source_rgba(0, 0, 0, 0.55)
    cr.set_line_width(7)
    cr.stroke()

    # front of the case
    rounded_rect(cr, MON_X0, MON_Y0, MON_X1 - MON_X0, MON_Y1 - MON_Y0, 48)
    fg = cairo.LinearGradient(0, MON_Y0, 0, MON_Y1)
    fg.add_color_stop_rgb(0.0, *PUTTY_LT)
    fg.add_color_stop_rgb(0.5, *PUTTY)
    fg.add_color_stop_rgb(1.0, *PUTTY_DK)
    cr.set_source(fg)
    cr.fill_preserve()
    side = cairo.LinearGradient(MON_X0, 0, MON_X1, 0)
    side.add_color_stop_rgba(0.0, *rgba(GOLD, 0.10))
    side.add_color_stop_rgba(0.2, *rgba(GOLD, 0.0))
    side.add_color_stop_rgba(0.8, *rgba(GREEN, 0.0))
    side.add_color_stop_rgba(1.0, *rgba(GREEN, 0.08))
    cr.set_source(side)
    cr.fill_preserve()
    cr.set_source_rgba(*rgba(GOLD_LT, 0.45))
    cr.set_line_width(3)
    cr.stroke()

    # the recess around the tube: four bevelled faces
    bx0, by0, bx1, by1 = SX - 72, SY - 66, SX + SW + 72, SY + SH + 66
    ix0, iy0, ix1, iy1 = SX - 14, SY - 14, SX + SW + 14, SY + SH + 14
    faces = [
        ([(bx0, by0), (bx1, by0), (ix1, iy0), (ix0, iy0)], 0.05),
        ([(bx1, by0), (bx1, by1), (ix1, iy1), (ix1, iy0)], 0.30),
        ([(bx0, by1), (bx1, by1), (ix1, iy1), (ix0, iy1)], 0.55),
        ([(bx0, by0), (bx0, by1), (ix0, iy1), (ix0, iy0)], 0.20),
    ]
    for quad, shade in faces:
        cr.move_to(*quad[0])
        for p in quad[1:]:
            cr.line_to(*p)
        cr.close_path()
        c = tuple(PUTTY_DK[i] + (PUTTY_LT[i] - PUTTY_DK[i]) * shade for i in range(3))
        cr.set_source_rgb(*c)
        cr.fill()
    crt_path(cr, SX - 22, SY - 22, SW + 44, SH + 44, 110, 18)
    cr.set_source_rgb(*VOID)
    cr.fill()

    # the tube
    cr.save()
    screen_path(cr)
    cr.clip()
    cr.set_source_rgb(*VOID)
    cr.paint()
    if screen_tex is not None:
        cr.save()
        cr.translate(SX, SY)
        cr.scale(1.0 / res, 1.0 / res)
        cr.set_source_surface(screen_tex, 0, 0)
        cr.get_source().set_filter(cairo.FILTER_GOOD)
        cr.paint()
        cr.restore()
    # glass: dark rim, a curved highlight, a soft reflection
    v = cairo.RadialGradient(SCX, SCY, SH * 0.30, SCX, SCY, SW * 0.68)
    v.add_color_stop_rgba(0.0, 0, 0, 0, 0.0)
    v.add_color_stop_rgba(1.0, 0, 0, 0, 0.55)
    cr.set_source(v)
    cr.paint()
    cr.move_to(SX + 40, SY + 260)
    cr.curve_to(SX + 60, SY + 80, SX + 260, SY + 34, SX + 620, SY + 30)
    cr.curve_to(SX + 300, SY + 70, SX + 110, SY + 140, SX + 40, SY + 260)
    cr.close_path()
    cr.set_source_rgba(1, 1, 1, 0.07)
    cr.fill()
    cr.restore()

    screen_path(cr)
    cr.set_source_rgba(*rgba(GREEN, 0.35))
    cr.set_line_width(2.0)
    cr.stroke()

    # maker's plate, rainbow stripe, knobs, power LED
    py = SY + SH + 140
    pixel_text(cr, ["MACHINE ELF"], MON_X0 + 120, py - 22, 6.4, GOLD, 0.95)
    stripe_cols = [GREEN, CYAN, VIOLET, MAGENTA, GOLD]
    for i, c in enumerate(stripe_cols):
        x = MON_X0 + 560 + i * 26
        cr.move_to(x, py + 20)
        cr.line_to(x + 18, py + 20)
        cr.line_to(x + 40, py - 22)
        cr.line_to(x + 22, py - 22)
        cr.close_path()
        cr.set_source_rgba(*rgba(c, 0.9))
        cr.fill()
    pixel_text(cr, ["//E"], MON_X0 + 720, py - 22, 6.4, GOLD_LT, 0.9)
    for i, kx in enumerate((MON_X1 - 420, MON_X1 - 300)):
        kg = cairo.RadialGradient(kx - 10, py - 12, 4, kx, py, 44)
        kg.add_color_stop_rgb(0.0, *PUTTY_LT)
        kg.add_color_stop_rgb(1.0, *PUTTY_DK)
        cr.arc(kx, py, 40, 0, 2 * math.pi)
        cr.set_source(kg)
        cr.fill_preserve()
        cr.set_source_rgba(*rgba(GOLD, 0.6))
        cr.set_line_width(2.5)
        cr.stroke()
        a = -2.2 + i * 1.9
        cr.move_to(kx + math.cos(a) * 12, py + math.sin(a) * 12)
        cr.line_to(kx + math.cos(a) * 34, py + math.sin(a) * 34)
        cr.set_source_rgba(*rgba(GOLD_LT, 0.95))
        cr.set_line_width(4)
        cr.stroke()
    lx = MON_X1 - 170
    lg = cairo.RadialGradient(lx, py, 2, lx, py, 40)
    lg.add_color_stop_rgba(0.0, *rgba(GREEN, 0.9))
    lg.add_color_stop_rgba(1.0, *rgba(GREEN, 0.0))
    cr.set_source(lg)
    cr.arc(lx, py, 40, 0, 2 * math.pi)
    cr.fill()
    cr.arc(lx, py, 9, 0, 2 * math.pi)
    cr.set_source_rgb(*GREEN)
    cr.fill()
    rounded_rect(cr, MON_X1 - 120, py - 26, 46, 52, 8)
    cr.set_source_rgb(*PUTTY_DK)
    cr.fill_preserve()
    cr.set_source_rgba(*rgba(GOLD, 0.5))
    cr.set_line_width(2)
    cr.stroke()


def base_unit(cr):
    x0, x1 = MON_X0 - 90, MON_X1 + 90
    rounded_rect(cr, x0, BASE_Y0, x1 - x0, BASE_Y1 - BASE_Y0, 20)
    g = cairo.LinearGradient(0, BASE_Y0, 0, BASE_Y1)
    g.add_color_stop_rgb(0.0, *PUTTY_LT)
    g.add_color_stop_rgb(1.0, *PUTTY_DK)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgba(*rgba(GOLD, 0.35))
    cr.set_line_width(2.5)
    cr.stroke()
    my = (BASE_Y0 + BASE_Y1) / 2
    pixel_text(cr, ["ELF-80"], x0 + 70, my - 20, 5.8, GOLD, 0.95)
    pixel_text(cr, ["HYPERSPACE SYSTEMS"], x0 + 70, my + 22, 2.6, GOLD_DK, 0.9)
    # two 5.25" drives
    for i in range(2):
        dx = x1 - 820 + i * 390
        rounded_rect(cr, dx, my - 44, 350, 88, 8)
        cr.set_source_rgb(*PUTTY_DK)
        cr.fill_preserve()
        cr.set_source_rgba(*rgba(GOLD, 0.3))
        cr.set_line_width(2)
        cr.stroke()
        cr.rectangle(dx + 30, my - 6, 290, 12)
        cr.set_source_rgb(*VOID)
        cr.fill()
        cr.rectangle(dx + 150, my - 30, 50, 16)
        cr.set_source_rgb(*PUTTY_LT)
        cr.fill()
        cr.arc(dx + 320, my + 28, 6, 0, 2 * math.pi)
        cr.set_source_rgb(*(RED if i == 0 else GREEN))
        cr.fill()
    # vents
    for i in range(10):
        vx = x0 + 760 + i * 30
        rounded_rect(cr, vx, my - 32, 12, 64, 6)
    cr.set_source_rgba(0, 0, 0, 0.55)
    cr.fill()


def keyboard(cr):
    tl, tr = (MON_X0 + 80, KB_Y0), (MON_X1 - 80, KB_Y0)
    bl, br = (MON_X0 - 90, KB_Y1), (MON_X1 + 90, KB_Y1)
    cr.move_to(*tl)
    cr.line_to(*tr)
    cr.line_to(*br)
    cr.line_to(*bl)
    cr.close_path()
    g = cairo.LinearGradient(0, KB_Y0, 0, KB_Y1)
    g.add_color_stop_rgb(0.0, *PUTTY)
    g.add_color_stop_rgb(1.0, *PUTTY_LT)
    cr.set_source(g)
    cr.fill_preserve()
    cr.set_source_rgba(*rgba(GOLD, 0.35))
    cr.set_line_width(2.5)
    cr.stroke()
    # front lip
    cr.move_to(*bl)
    cr.line_to(*br)
    cr.line_to(br[0], br[1] + 26)
    cr.line_to(bl[0], bl[1] + 26)
    cr.close_path()
    cr.set_source_rgb(*PUTTY_DK)
    cr.fill()

    rows = [15, 15, 14, 13, 9]
    pad_t, pad_b = 0.10, 0.06
    for r, keys in enumerate(rows):
        f0 = pad_t + (1 - pad_t - pad_b) * r / len(rows)
        f1 = pad_t + (1 - pad_t - pad_b) * (r + 0.82) / len(rows)
        ya, yb = KB_Y0 + (KB_Y1 - KB_Y0) * f0, KB_Y0 + (KB_Y1 - KB_Y0) * f1
        la = tl[0] + (bl[0] - tl[0]) * f0 + 40
        ra = tr[0] + (br[0] - tr[0]) * f0 - 40
        lb = tl[0] + (bl[0] - tl[0]) * f1 + 40
        rb = tr[0] + (br[0] - tr[0]) * f1 - 40
        if r == 4:  # space bar row
            la, ra = la + (ra - la) * 0.18, ra - (ra - la) * 0.18
            lb, rb = lb + (rb - lb) * 0.18, rb - (rb - lb) * 0.18
        ka, kb = (ra - la) / keys, (rb - lb) / keys
        for k in range(keys):
            if r == 4 and 2 <= k <= 6:
                if k != 2:
                    continue
                span = 5
            else:
                span = 1
            q = [(la + ka * k + 5, ya), (la + ka * (k + span) - 5, ya),
                 (lb + kb * (k + span) - 5, yb), (lb + kb * k + 5, yb)]
            cr.move_to(*q[0])
            for p in q[1:]:
                cr.line_to(*p)
            cr.close_path()
            cr.set_source_rgb(*PUTTY_LT)
            cr.fill_preserve()
            cr.set_source_rgba(*rgba(GOLD, 0.30))
            cr.set_line_width(1.4)
            cr.stroke()
            cr.move_to(q[3][0], q[3][1])
            cr.line_to(q[2][0], q[2][1])
            cr.line_to(q[2][0], q[2][1] + 5)
            cr.line_to(q[3][0], q[3][1] + 5)
            cr.close_path()
            cr.set_source_rgb(*PUTTY_DK)
            cr.fill()
            # glowing legends on a few keys
            if (r * 7 + k * 3) % 5 == 0:
                mx = (q[0][0] + q[2][0]) / 2
                my = (q[0][1] + q[2][1]) / 2
                cr.rectangle(mx - 3, my - 3, 6, 6)
                cr.set_source_rgba(*rgba(GREEN if k % 2 else GOLD, 0.8))
                cr.fill()


# ------------------------------------------------- what the screen shows ---

def render_screen_content(prev, res, depth_index):
    sw, sh = int(SW * res), int(SH * res)
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, sw, sh)
    cr = cairo.Context(surf)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    cr.scale(res, res)
    cr.translate(-SX, -SY)

    cr.set_source_rgb(*VOID)
    cr.paint()
    # the level behind, a little dimmer for depth
    paint_crop(cr, prev, SX, SY, SW, SH, 0.86)

    # two more elves peering over the main one's shoulders
    for s in (-1, 1):
        elf(cr, ELF_X + s * 390, 650, 250, rim=VIOLET if s < 0 else MAGENTA, body_alpha=0.55,
            bright=0.75, halo=0.5)
    # the elf breaking out, its arms reaching for the glass
    elf(cr, ELF_X, ELF_Y, ELF_U, rim=GREEN, body_alpha=0.55, arms_to=HOLES)

    # boot screen
    pixel_text(cr, ["**** MACHINE ELF //E  64K ****", "38911 HYPERSPACE BYTES FREE"],
               SCX, SY + 34, 4.4, GREEN, 0.85, align="center")
    pixel_text(cr, ["]RUN ELF.BAS", "READY.@"], SCX, SY + SH - 98, 4.4, GREEN, 0.85, align="center")

    # scanlines, drawn before the tube curvature so they curve with it
    cr.set_source_rgba(0, 0, 0, 0.32)
    y = SY
    while y < SY + SH:
        cr.rectangle(SX, y, SW, 1.8)
        y += 4.5
    cr.fill()
    return surf


def crt_process(surf, res, tmpdir, tag):
    """Bloom and tube curvature, by ImageMagick, on the screen picture."""
    src = os.path.join(tmpdir, f"scr-{tag}.png")
    dst = os.path.join(tmpdir, f"crt-{tag}.png")
    surf.write_to_png(src)
    blur = max(4, int(14 * res))
    subprocess.run([
        "magick", src, "-alpha", "off",
        "(", "+clone", "-level", "35%,100%", "-blur", f"0x{blur}", "-evaluate", "multiply", "0.75", ")",
        "-compose", "screen", "-composite",
        "-virtual-pixel", "black", "-distort", "Barrel", "0.0 0.0 0.075 0.925",
        dst,
    ], check=True)
    return cairo.ImageSurface.create_from_png(dst)


# ------------------------------------------------------------- whole scene ---

def render_canvas(prev, screen_tex, res, variant, camera=None):
    surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H)
    cr = cairo.Context(surf)
    cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.set_line_cap(cairo.LINE_CAP_ROUND)
    rng = random.Random(1984)

    cr.save()
    if camera:
        z, fx, fy = camera
        cr.translate(W / 2, H / 2)
        cr.scale(z, z)
        cr.translate(-fx, -fy)

    backdrop(cr, rng, variant)
    for (x, y, w, rot, a) in pod_layout(variant):
        pod(cr, prev, x, y, w, rot, a)

    cr.save()
    cr.translate(W / 2, H / 2)
    cr.scale(STAGE_SCALE, STAGE_SCALE)
    cr.translate(-W / 2, -H / 2)

    keyboard(cr)
    base_unit(cr)
    monitor(cr, screen_tex, res)

    # the glass breaks
    cr.save()
    screen_path(cr)
    cr.clip()
    for s in (-1, 1):
        cracks(cr, random.Random(77 + s), *HOLES[s])
    for s in (-1, 1):
        hole(cr, random.Random(91 + s), *HOLES[s])
    cr.restore()

    # impact flash where each arm punched through
    for s in (-1, 1):
        x, y = HOLES[s]
        g = cairo.RadialGradient(x, y, 10, x, y, 420)
        g.add_color_stop_rgba(0.0, *rgba(WHITE, 0.30))
        g.add_color_stop_rgba(0.25, *rgba(GOLD, 0.18))
        g.add_color_stop_rgba(1.0, *rgba(GOLD, 0.0))
        cr.set_source(g)
        cr.arc(x, y, 420, 0, 2 * math.pi)
        cr.fill()

    shards = {s: make_shards(random.Random(300 + s), *HOLES[s], s) for s in (-1, 1)}
    for s in (-1, 1):
        draw_shards(cr, [sh for sh in shards[s] if sh[0] < 300])
    for s in (-1, 1):
        hand(cr, s, *WRISTS[s], HAND_L, HAND_TILT, HOLES[s])
    for s in (-1, 1):
        draw_shards(cr, [sh for sh in shards[s] if sh[0] >= 300])

    cr.restore()
    cr.restore()
    return surf


def render(out, depth, variant):
    camera = None
    final_res = 1.0
    if variant == 2:
        fx, fy = stage_to_canvas(SCX, SCY + 40)
        camera = (1.75, fx, fy)
        final_res = 1.75 * STAGE_SCALE * 1.1

    with tempfile.TemporaryDirectory(prefix="elf-recursion-") as tmp:
        prev = None
        # inner levels first, each one becoming the next one's screen
        for level in range(depth):
            tex = crt_process(render_screen_content(prev, 1.0, level), 1.0, tmp, f"{level}")
            prev = render_canvas(prev, tex, 1.0, variant)
        if camera:
            tex = crt_process(render_screen_content(prev, final_res, depth), final_res, tmp, "final")
            prev = render_canvas(prev, tex, final_res, variant, camera)
        prev.write_to_png(out)
    print(out)


def main():
    argv = sys.argv[1:]
    if not argv:
        print(__doc__)
        return 1
    out = argv[0]
    depth, variant = 6, 1
    if "--depth" in argv:
        depth = int(argv[argv.index("--depth") + 1])
    if "--variant" in argv:
        variant = int(argv[argv.index("--variant") + 1])
    render(out, depth, variant)
    return 0


if __name__ == "__main__":
    sys.exit(main())
