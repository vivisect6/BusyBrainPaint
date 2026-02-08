# CLAUDE.md — BusyBrainPaint

A Windows desktop paint-by-numbers game with procedural mandala puzzles, designed for relaxing play while listening to audiobooks.

## Quick Reference

- **Engine**: pygame-ce
- **Python**: Latest version compatible with dependencies
- **Dependencies**: pygame-ce, numpy, pillow (opencv and numba optional for generation)
- **Run**: `python main.py`
- **Display**: Fullscreen only
- **Input**: Gamepad only (no keyboard fallback)
- **Audio**: None (intentionally silent for audiobook listening)

## Code Style

- **Type hints**: Required on all functions
- **Docstrings**: Google style
- **Sections marked "Locked"**: Do not change or question these decisions

---

## Core Game Concept

A puzzle consists of:
- A **region-id map**: 2D array where each pixel stores an integer region ID
- A **palette**: list of colors (RGB) + indices (numbers)
- A mapping `region_id -> palette_index` defining the correct number/color for each region

Runtime gameplay:
- Player selects a palette color (number) with LB/RB
- Player selects a region with right stick (adjacency navigation)
- Player holds A to fill; larger regions take longer (linear with area)
- Wrong color still fills during hold, then shakes + fades out and is cleared
- Autosave after each successful fill

---

## Application Flow

### Main Menu
- **New Game**: Opens settings to configure preset/scale/colors, then generates puzzle
- **Continue**: Resumes from autosave (disabled if no save exists)
- **Gallery**: View completed puzzle snapshots

### Completion
When all regions are filled:
- Snapshot the completed puzzle as an image
- Save to gallery
- Return to main menu (or show completion screen first)

---

## Controller Scheme (Locked)

### Palette selection
- **LB/RB**: previous/next palette index (wrap)

### Zoom
- **RT (hold)**: zoom in continuously to max clamp
- **LT (hold)**: zoom out continuously to min clamp

### Camera pan/view
- **Left stick**: pan camera (world pixels/sec scaled by zoom)
- **L3**: snap/center camera on selected region
- Selection change should **nudge camera** to keep selection comfortably on-screen (no hard snap)

### Region selection
- **Right stick**: move selection between regions via adjacency graph + centroid direction
  - Prefer unfilled regions when choosing among candidates
  - Stick debounce + repeat (e.g., 180ms initial, 90ms repeat)

#### Right-stick selection algorithm
- `d = normalize((rx, ry))`
- For each `n in adj[current]`:
  - `v = normalize(centroid[n] - centroid[current])`
  - `score = dot(v, d)`
- Choose highest score > threshold (e.g., 0.3)
- Tiebreakers:
  - prefer unfilled
  - then nearer centroid distance

### D-pad quadrant jumping (Locked)
D-pad does **non-adjacent jumps** to the nearest region in the pressed direction, based on **world/puzzle coordinates**.
- **Right**: choose nearest region with `dx > 0`
- **Left**: choose nearest region with `dx < 0`
- **Down**: choose nearest region with `dy > 0`
- **Up**: choose nearest region with `dy < 0`

Scoring (example):
- Right/Left: `score = abs(dx) + k*abs(dy)`
- Up/Down: `score = abs(dy) + k*abs(dx)`
- Filter by direction sign first; choose min score
- Prefer unfilled; fallback to filled

Suggested `k`: 1.5–3.0 (tunes "stay on axis" feel)

### Fill action (Hold)
- **Hold A**: begin filling selected region over time
- Cancel fill on **movement**:
  - selection changes (right stick / D-pad)
  - camera pans beyond deadzone (left stick)
  - zoom changes beyond deadzone (triggers)

Fill time:
- `fill_time = clamp(area / pixels_per_second, min_time, max_time)`
- Defaults:
  - `pixels_per_second = 12000`
  - `min_time = 0.15s`
  - `max_time = 2.0s`
- Linear with region area.

Strict wrong-color behavior:
- Wrong color: allow fill preview, then **shake + fade out**, and clear (no progress).

---

## Data Model (Puzzle Runtime Structures)

Inputs:
- `region_ids`: HxW int array (region id per pixel)
- `palette`: list of RGB colors + display numbers
- `region_color`: mapping `region_id -> palette_index`

Precompute at load:
- `region_area[region_id]`
- `region_bbox[region_id]`
- `region_centroid[region_id]`
- `region_runs[region_id] -> list[(y, x_start, x_end)]` (run-length spans; recommended)
- `adj[region_id] -> set(neighbor_region_ids)` adjacency graph
- `filled[region_id] -> bool`

Prefer contiguous region IDs 0..N-1. Remap at load if needed.

---

## Rendering (Layered Surfaces)

Avoid redrawing full board per fill:

1. `outline_surface` (static): boundaries + region numbers
2. `base_surface` (optional static): paper/texture or faint guide
3. `filled_surface` (dynamic): committed correct fills only
4. `temp_fill_surface` (dynamic): preview fill while holding A (cleared after commit/reject)
5. `highlight_surface` (dynamic): selected region highlight, updated on selection change

Camera:
- Maintain `(cam_x, cam_y, zoom)`; transform world -> screen on blit.

---

## Region Filling + Highlighting (Runs-Based)

### Build run spans
Scan rows, record contiguous runs of constant region_id:
- Append `(y, x0, x1)` to `region_runs[region_id]`
- Accumulate bbox, area, centroid sums

### Commit fill (correct)
Draw all runs for region onto `filled_surface` in palette color.

### Preview fill (during hold)
Draw runs progressively (optional) or simply draw full region to `temp_fill_surface` and animate alpha/progress.
Recommended: keep preview cheap; "progress ring" can show timing.

### Wrong fill reject (shake + fade)
- Keep wrong fill only in `temp_fill_surface`
- Play reject animation:
  - shake: offset blit of `temp_fill_surface` by small alternating offsets for ~200–350ms
  - fade: reduce alpha to 0 over same window
- Clear `temp_fill_surface` at end

Cancel behavior:
- If canceled mid-hold: clear preview immediately.

---

## Numbers Inside Regions (Locked)

Render numbers inside regions.
Practical rule:
- Draw numbers for regions above an area threshold.
- For tiny regions: show number only when selected (or when zoomed in enough).

---

## Saving / Loading (Autosave Locked)

Autosave after each successful fill commit.

Save content:
- puzzle identifier (preset + seed + params) OR filename
- filled state (bitset preferred)
- selected palette index
- selected region id
- camera state: pan + zoom
- settings snapshot (scale/colors/preset) for consistency

File:
- `save.json` (+ optional `progress.bin` bitset)

### Gallery
- Store completed puzzle snapshots as PNG images
- Gallery screen allows browsing saved completions

---

## Puzzle File Format (Suggested)

Exported puzzle:
- `puzzle.json`
  - version
  - width/height
  - palette (RGB + label/number)
  - region_color array
  - generator preset id + params + seed (for regen)
- `region_ids.png`
  - 24-bit RGB encoding: `id = r + (g<<8) + (b<<16)`

Runtime:
- Load region_ids.png -> NumPy int map
- Load puzzle.json -> palette + region_color
- Precompute runs/adj/centroids

---

## Procedural Content Plan (Mandala-Focused Presets)

Fractals are out-of-scope for v1. Use generators that reliably produce **closed, fillable regions**.

All presets must support:
- `seed` (deterministic)
- `scale` (resolution / complexity)
- `num_colors` (palette size)
- region cleanup: merge tiny regions, smooth boundaries, remove noise islands

### Preset A: Voronoi Mandala (TOP PRIORITY)
**Look:** stained-glass / organic cell mandalas
**Method:**
- Generate points in a wedge, rotate-copy around center (symmetry N)
- Compute Voronoi diagram, clip to circle
- Optionally Lloyd relax 1-3 iterations for smoother cells

**Menu settings:** Size, Colors, Palette, Symmetry (4-16)

**Parameters:**
- `symmetry_slices` (menu: 4-16)
- `point_count` (auto-scaled by detail multiplier)
- `radial_bias` (internal, default 0.5)
- `relax_iters` (internal, fixed at 1)

**Why:** Always closed cells, scalable complexity, very robust.

### Preset B: Stained Glass (Voronoi + Thick "Lead")
**Look:** bold outlines, big satisfying fills
**Method:**
- Start from Voronoi cells with radial symmetry
- Render thick outlines ("lead")
- Each glass pane becomes a fillable region; lead lines form borders

**Menu settings:** Size, Colors, Palette, Symmetry (4-16), Outline (Thin/Medium/Thick)

**Parameters:**
- `symmetry_slices` (menu: 4-16)
- `outline_thickness` (menu: Thin=2, Medium=4, Thick=6; scaled by detail multiplier)
- `point_count` (auto-scaled by detail multiplier)
- `edge_detail_boost` (internal, default 0.5)
- `use_symmetry` (internal, always True)

**Why:** Perfectly matches paint-by-numbers filling.

### Preset E: Truchet Tile Mandala (Not implemented)
**Look:** curvy tile paths forming regions
**Method:**
- Place Truchet tiles on a grid; mirror/rotate for symmetry
- Interpret tile curves as boundaries; fill regions between paths

**Parameters:**
- `grid_size`
- `tile_set` (2-4 tile variants)
- `symmetry_slices` or mirror axes

**Why:** High variety with simple rules; ensure region cleanup.

### Preset F: Topographic Contour Mandala (Not implemented)
**Look:** contour bands like elevation rings
**Method:**
- Generate radial noise field; take contour levels into bands
- Segment bands into regions; aggressively merge skinny islands

**Parameters:**
- `levels` (bands)
- `noise_scale`
- `radial_falloff`

**Why:** Pretty, but requires strong merging/smoothing to avoid thin regions.

#### Implementation Status
Presets A-B are implemented. Presets E and F are future work.

---

## Scale + Color Count Selectability (Locked)

The settings UI is controller-friendly and shows **per-generator options** — the menu rebuilds dynamically when the preset changes.

### Common settings (all presets)
- **Preset**: Voronoi Mandala / Stained Glass
- **Size**: Small (256px) / Medium (384px) / Large (512px) / Extra Large (640px)
  - Each size has a detail multiplier (0.5 / 0.75 / 1.0 / 1.25) that auto-scales generator params
- **Colors**: 6 / 8 / 12 / 16 / 24
- **Palette**: Random / Classic / Pastel / Jewel / Earth / Ocean / Sunset / Berry / Autumn / Neon / Stained Glass
  - 10 curated 24-color palettes defined in `palettes.py`; each ordered so any prefix (6/8/12/16/24) is maximally distinguishable
  - "Random" picks a palette at generation time

### Per-generator settings
| Setting | Voronoi | Stained Glass |
|---|---|---|
| Symmetry (4-16) | yes | yes |
| Outline (Thin/Medium/Thick) | — | yes |

Implementation details:
- `_build_menu()` is called on init and whenever the preset selector changes
- `_apply_settings()` reads menu items by label to update PuzzleSettings
- Keep determinism: save `preset + params + seed` so puzzles regenerate identically

---

## Milestones (All Complete)

1. ~~Implement loader for stub puzzle assets (`region_ids.png + puzzle.json`)~~
2. ~~Precompute runs, centroids, adjacency~~
3. ~~Implement selection navigation (right stick + prefer unfilled) and D-pad quadrant jump~~
4. ~~Implement camera pan + trigger zoom + nudge + L3 snap~~
5. ~~Implement hold-to-fill (temp preview -> commit/reject) + cancel-on-movement~~
6. ~~Implement autosave + load~~
7. ~~Implement numbers-in-regions rendering with thresholds~~
8. ~~Add generator presets A-B (export to puzzle format)~~
9. ~~Add settings menu for preset/scale/colors (with per-generator options)~~
10. ~~Add main menu (New Game / Continue / Gallery)~~
11. ~~Add completion snapshot + gallery viewer~~
