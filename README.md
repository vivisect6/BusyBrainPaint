# BusyBrainPaint

A gamepad-only paint-by-numbers game for Windows. Generate mandala puzzles procedurally or convert images into puzzles. Designed for relaxing play while listening to audiobooks — no audio, fullscreen, controller-driven.

## Requirements

- Python 3.12+
- Xbox-compatible gamepad
- Dependencies: `pygame-ce`, `numpy`, `pillow`, `scipy`

```
pip install pygame-ce numpy pillow scipy
```

## Quick Start

### Play a generated mandala

```
python generate_puzzle.py voronoi_mandala puzzles/current --size 768 --colors 12
python main.py
```

### Play from an image

```
python image_to_puzzle.py photo.jpg
python main.py
```

Then select **Continue** from the main menu.

## Controls

| Input | Action |
|-------|--------|
| **LB / RB** | Cycle palette color |
| **Right stick** | Move selection between adjacent regions |
| **D-pad** | Jump to nearest region in that direction |
| **Hold A** | Fill selected region with current color |
| **Left stick** | Pan camera |
| **RT / LT** | Zoom in / out |
| **L3** | Snap camera to selected region |

Wrong color fills play a shake + fade animation and don't count. Progress autosaves after each correct fill.

## Generating Puzzles

### Procedural mandalas

```
python generate_puzzle.py <preset> <output_dir> [options]
```

**Presets:**
- `voronoi_mandala` — Stained-glass organic cell mandalas
- `stained_glass` — Bold outlines with big satisfying fills

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--size` | 768 | Puzzle size in pixels |
| `--colors` | 6 | Palette size (6, 8, 12, 16, or 24) |
| `--seed` | random | Random seed for reproducibility |
| `--symmetry` | 8 | Symmetry slices (4–16) |
| `--points` | 30 | Voronoi point count |
| `--outline` | 4 | Lead line thickness (stained glass only) |

### From an image

```
python image_to_puzzle.py <image_path> [output_dir] [options]
```

Converts a photo or illustration into a paint-by-numbers puzzle. Works best with flat vector-style art — see `imageprompt.md` for a ChatGPT prompt template to generate ideal source images.

**How it works:**
1. Resize image to target size
2. Quantize to N colors (median cut) — these become the puzzle palette
3. Label connected same-color regions
4. Merge tiny regions and smooth boundaries
5. Subdivide large regions with Voronoi seeds to reach the target count
6. Export as `puzzle.json` + `region_ids.png`

**Options:**

| Flag | Default | Description |
|------|---------|-------------|
| `--colors` | 12 | Palette size (6, 8, 12, 16, or 24) |
| `--size` | 768 | Longest edge in pixels |
| `--target-regions` | 300 | Target region count (large regions are subdivided) |
| `--min-area` | 20 | Min region area before merging |
| `--blur` | 1.0 | Pre-quantization blur radius (0 to disable) |
| `--seed` | random | Random seed for reproducible subdivision |

Output defaults to `puzzles/current` and clears any existing save.

## Main Menu

- **New Game** — Configure and generate a new mandala puzzle
- **Continue** — Resume from autosave
- **Gallery** — Browse completed puzzle snapshots

## Project Structure

```
main.py                 Game entry point
main_menu.py            Main menu screen
settings.py             New Game settings UI
generate_puzzle.py      CLI mandala generator
image_to_puzzle.py      CLI image-to-puzzle converter
imageprompt.md          ChatGPT prompt guide for source images

puzzle_loader.py        Loads puzzle files into runtime structures
save_manager.py         Autosave / load progress
camera.py               Camera pan + zoom
selection.py            Region selection navigation
fill_controller.py      Hold-to-fill mechanic
input_handler.py        Gamepad input mapping
menu.py                 Reusable menu widget
palettes.py             10 curated color palettes

generators/
  base.py               Base generator class
  cleanup.py            Region cleanup utilities (merge, smooth, remap)
  export.py             Puzzle export (puzzle.json + region_ids.png)
  voronoi_mandala.py    Voronoi Mandala generator
  stained_glass.py      Stained Glass generator
```

## Puzzle Format

A puzzle is a directory containing:

- **`puzzle.json`** — palette, region-to-color mapping, generator metadata, non-playable region list
- **`region_ids.png`** — region ID map encoded as RGB (`id = r + (g << 8) + (b << 16)`)

The game precomputes adjacency graphs, centroids, bounding boxes, and run-length spans at load time.
