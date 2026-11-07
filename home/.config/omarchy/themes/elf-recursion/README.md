# Elf Recursion

An 80s green-screen computer adrift in hyperspace, and the machine elf breaking
out of it. Inside the CRT the elf pushes both gold-clawed hands out through the
glass at you, two more elves peering over its shoulders. Behind them, inside
the screen, the whole scene repeats, and repeats. Small CRTs drift through the
void showing the same scene, so every little elf has the recursion inside it too.

Void-violet glass, acid phosphor green, machine-elf gold, ultraviolet and hot
magenta at the edges. Dark mode only.

## Files

| File | What it is |
|---|---|
| `colors.toml` | The palette, with gold in the yellows and the window-border gradient |
| `shell.toml` | Bar, panels, notifications, lock. Bar fully opaque (`background-alpha = 1.0`) |
| `icons.theme` | Icon theme |
| `backgrounds/` | `1-elf-recursion` hero, `2-deeper-down` pushed in on the hands, `3-the-swarm` void full of elf CRTs |
| `preview.png` | Theme-switcher preview |
| `make-backgrounds.py` | The artwork and the recursion, drawn with cairo |
| `make-backgrounds.sh` | Renders all three in parallel and gives them the CRT finish |

## Regenerating the art

```bash
./make-backgrounds.sh      # ~12 s for all three at 3840x2160
python3 make-backgrounds.py out.png --variant 1 --depth 6   # one raw render
```

## How the recursion works

It is rendered for real, from the inside out. Each pass draws the whole
canvas; that image is then cropped to 4:3, bloomed, scanlined and
barrel-distorted by ImageMagick like a picture on a tube, and becomes the
screen (and every floating mini CRT) of the next pass. `--depth` is the number
of passes.

`STAGE_SCALE` keeps the computer and the hands inside the band a 21:9 panel
keeps, since Omarchy paints backgrounds `PreserveAspectCrop`.

The 5x7 boot-screen font is built into the script, so it needs nothing
installed beyond python-cairo and ImageMagick.
