#!/bin/bash
# Elf Recursion - render the wallpapers and finish them like an 80s CRT.
#
# make-backgrounds.py renders the recursion (each inner screen already gets
# its own tube curvature, bloom and scanlines). This pass treats the whole
# frame as a picture on a tube: phosphor bloom, convergence error, an
# aperture-grille mask, scanlines, grain, and a vignette.

set -euo pipefail

HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT="$HERE/backgrounds"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT
mkdir -p "$OUT"

W=3840
H=2160

# The tube's mask: soft scanlines every 4 rows and a faint RGB aperture grille
# every 6 columns. Coarse enough not to moire when scaled to 2560 wide.
python3 - "$TMP/mask.png" "$W" "$H" <<'PY'
import sys, cairo
out, w, h = sys.argv[1], int(sys.argv[2]), int(sys.argv[3])
s = cairo.ImageSurface(cairo.FORMAT_RGB24, w, h)
cr = cairo.Context(s)
cr.set_source_rgb(1, 1, 1)
cr.paint()
cols = [(1.0, 0.90, 0.90), (0.90, 1.0, 0.90), (0.90, 0.90, 1.0)]
for x in range(0, w, 6):
    for i, c in enumerate(cols):
        cr.set_source_rgb(*c)
        cr.rectangle(x + i * 2, 0, 2, h)
        cr.fill()
for y in range(0, h, 4):
    cr.set_source_rgba(0, 0, 0, 0.26)
    cr.rectangle(0, y, w, 1.5)
    cr.fill()
    cr.set_source_rgba(0, 0, 0, 0.10)
    cr.rectangle(0, y + 1.5, w, 0.8)
    cr.fill()
# rolling interlace bands
for y in range(0, h, 180):
    cr.set_source_rgba(0, 0, 0, 0.06)
    cr.rectangle(0, y, w, 46)
    cr.fill()
s.write_to_png(out)
PY

render() { # name, variant, depth
  local name="$1" variant="$2" depth="$3"
  python3 "$HERE/make-backgrounds.py" "$TMP/$name.raw.png" --variant "$variant" --depth "$depth" >/dev/null

  magick "$TMP/$name.raw.png" -alpha off \
    \( +clone -level 38%,100% -blur 0x40 -evaluate multiply 0.70 \) -compose screen -composite \
    \( +clone -level 55%,100% -blur 0x9  -evaluate multiply 0.55 \) -compose screen -composite \
    -channel R -roll -4+0 +channel \
    -channel B -roll +4+1 +channel \
    "$TMP/mask.png" -compose multiply -composite \
    -level 0%,80% \
    -attenuate 0.08 +noise Gaussian \
    \( -size ${W}x${H} radial-gradient:'#ffffff'-'#5a5a5a' -evaluate pow 0.45 \) -compose multiply -composite \
    -modulate 103,118,100 -sigmoidal-contrast 1.3,45% \
    -quality 93 -type TrueColor "$OUT/$name.jpg"
  echo "  $name.jpg"
}

echo "render:"
render "1-elf-recursion" 1 6 &
render "2-deeper-down"   2 6 &
render "3-the-swarm"     3 5 &
wait
echo "done -> $OUT"
