#!/bin/bash
set -e
OUT="$HOME/.config/omarchy/themes/machine-elf/backgrounds"
W=3840; H=2160

# 1D iridescent colour ramp: void -> teal -> phosphor -> acid -> cyan -> azure -> violet -> magenta -> gold -> void
cols=( '#000205' '#051619' '#07463a' '#00b877' '#00ffa3' '#38e8ff' '#2050ff' '#7a2fd0' '#ff3ff0' '#ffb43d' '#1a0410' '#02060a' )
rm -f part_*.png
for ((i=0; i<${#cols[@]}-1; i++)); do magick -size 1x96 "gradient:${cols[i]}-${cols[i+1]}" "part_$i.png"; done
magick $(ls part_*.png | sort -V) -append -resize 1x1024! clut.png

# soft vignette mask (never fully black at the edges)
magick -size ${W}x${H} radial-gradient:'#ffffff'-'#606060' -evaluate pow 0.35 vm.png

# --- 1: hyperspace bloom ---
magick -size ${W}x${H} -seed 42 plasma:fractal -blur 0x2.4 -colorspace gray -auto-level -swirl 220 nebula_g.png
magick nebula_g.png -evaluate pow 2.0 -level 0%,96% clut.png -clut -colorspace sRGB \
  -modulate 100,165,100 -sigmoidal-contrast 1.2,55% -evaluate multiply 0.80 \
  vm.png -compose multiply -composite -type TrueColor -quality 92 "$OUT/1-hyperspace-bloom.jpg"

# --- 2: machine elf (kaleidoscopic entity over the void) ---
MS=$(( H * 96 / 100 ))
magick -size ${MS}x${MS} -seed 9 plasma:fractal -colorspace gray -auto-level -blur 0x1.4 \
  -distort DePolar 0 -crop ${MS}x$((MS/4))+0+0 +repage -auto-level \
  \( +clone -flop \) +append \( +clone -flip \) -append \
  -virtual-pixel black -background black -distort Polar 0 +repage -auto-level mand_g.png
magick mand_g.png -level 0%,90% clut.png -clut -colorspace sRGB \
  -modulate 100,155,100 -evaluate multiply 0.80 mand_c.png
magick -size ${W}x${H} xc:'#01030a' \
  \( nebula_g.png -evaluate pow 3.4 -level 0%,88% clut.png -clut -colorspace sRGB -modulate 85,140,100 -evaluate multiply 0.50 \) -compose screen -composite \
  \( mand_c.png -resize x${H} \) -gravity center -compose screen -composite \
  \( mand_c.png -resize x${H} -blur 0x48 -evaluate multiply 0.5 \) -gravity center -compose screen -composite \
  vm.png -compose multiply -composite -type TrueColor -quality 92 "$OUT/2-machine-elf.jpg"

# --- 3: entity through the CRT ---
magick -size 256x256 xc:'#05090d' -stroke '#22ffb870' -strokewidth 4 -draw "line 0,0 255,0" -draw "line 0,0 0,255" grid_tile.png
magick -size ${W}x${H} tile:grid_tile.png grid.png
magick -size 1x6 xc:'#0000006a' -size 1x6 xc:'#ffffff00' -append scan_1x12.png
magick -size ${W}x${H} tile:scan_1x12.png scan.png
magick -size ${W}x${H} xc:'#050a0e' \
  \( -size ${W}x${H} -seed 5 plasma:fractal -colorspace gray -auto-level -blur 0x28 -level 0%,62% \) -compose multiply -composite \
  \( -size ${W}x${H} xc:black -fill '#00ffa3' -draw "circle $((W*42/100)),$((H*46/100)) $((W*42/100)),$((H*28/100))" -blur 0x140 \) -compose screen -composite \
  \( -size ${W}x${H} xc:black -fill '#ff2fd6' -draw "circle $((W*10/100)),$((H*88/100)) $((W*10/100)),$((H*74/100))" -blur 0x160 -evaluate multiply 0.85 \) -compose screen -composite \
  \( -size ${W}x${H} xc:black -fill '#7a5cff' -draw "circle $((W*90/100)),$((H*14/100)) $((W*90/100)),$((H*3/100))" -blur 0x160 -evaluate multiply 0.75 \) -compose screen -composite \
  \( mand_c.png -resize x$((H*85/100)) -evaluate multiply 0.34 \) -gravity center -compose screen -composite \
  grid.png -compose screen -composite \
  scan.png -compose multiply -composite -type TrueColor -quality 92 "$OUT/3-entity-through-the-crt.jpg"

magick "$OUT/1-hyperspace-bloom.jpg" -resize 1920x preview.png
identify -format '%f %wx%h mean=%[fx:mean] ch=%[channels]\n' "$OUT"/*.jpg
