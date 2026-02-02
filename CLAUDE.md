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

**Parameters:**
- `symmetry_slices` (6-24)
- `point_count` (scaled with difficulty)
- `radial_bias` (more points near edge vs center)
- `relax_iters` (0-3)
- `outline_thickness`

**Why:** Always closed cells, scalable complexity, very robust.

### Preset B: Polar Harmonics (Petals/Rings/Spokes)
**Look:** classic mandala petals, rosettes, lace-like rings
**Method:**
- Work in polar coords; fold theta into `symmetry_slices`
- Define layers with sine/cos harmonics; threshold into bands
- Combine rings + petals + spokes with boolean ops

**Parameters:**
- `symmetry_slices`
- `ring_count`
- `petal_freq` + `petal_depth`
- `spoke_count` + `spoke_width`
- `jitter` (tiny, optional, to avoid perfect repetition)

**Why:** Deterministic, controllable, and produces clean regions.

### Preset C: Geometric Tiling (Clipped to Circle)
**Look:** crisp mosaic / "islamic tile" vibes
**Method:**
- Build base tiling (hex/tri/square) in world coords
- Apply radial symmetry (rotate or polar-warp)
- Clip to circle; optionally overlay multiple tiling layers

**Parameters:**
- `tiling_type` (hex/tri/square)
- `cell_size`
- `symmetry_slices` (optional)
- `warp_strength` (0-small)
- `layer_count` (1-3)

**Why:** Crisp lines, very readable, excellent for numbers-in-cells.

### Preset D: Stained Glass (Voronoi + Thick "Lead")
**Look:** bold outlines, big satisfying fills
**Method:**
- Start from Voronoi cells (can be non-symmetric or symmetric)
- Render thick outlines ("lead")
- Optionally add a second pass of smaller cells near edge

**Parameters:**
- `outline_thickness` (key)
- `point_count`
- `symmetry_slices` (optional)
- `edge_detail_boost` (more points near boundary)

**Why:** Perfectly matches paint-by-numbers filling.

### Preset E: Truchet Tile Mandala (Secondary)
**Look:** curvy tile paths forming regions
**Method:**
- Place Truchet tiles on a grid; mirror/rotate for symmetry
- Interpret tile curves as boundaries; fill regions between paths

**Parameters:**
- `grid_size`
- `tile_set` (2-4 tile variants)
- `symmetry_slices` or mirror axes

**Why:** High variety with simple rules; ensure region cleanup.

### Preset F: Topographic Contour Mandala (Optional, needs cleanup)
**Look:** contour bands like elevation rings
**Method:**
- Generate radial noise field; take contour levels into bands
- Segment bands into regions; aggressively merge skinny islands

**Parameters:**
- `levels` (bands)
- `noise_scale`
- `radial_falloff`

**Why:** Pretty, but requires strong merging/smoothing to avoid thin regions.

#### Preset Selection Recommendation for v1
Implement in this order:
1. Voronoi Mandala (A)
2. Polar Harmonics (B)
3. Geometric Tiling (C)
4. Stained Glass (D)
Then add E/F if desired.

---

## Scale + Color Count Selectability (Locked)

Provide a settings UI (controller-friendly) to choose:
- `preset` (A/B/C/D/...)
- `scale` (e.g., Small/Medium/Large) affecting resolution + detail
- `num_colors` (e.g., 12/24/36/48)
- optional: `symmetry_slices`, outline thickness, etc.

Implementation guidance:
- Use "difficulty presets" that map to concrete params per generator
- Keep determinism: save `preset + params + seed` so puzzles regenerate identically

---

## Milestones (Do in Order)

1. Implement loader for stub puzzle assets (`region_ids.png + puzzle.json`)
2. Precompute runs, centroids, adjacency
3. Implement selection navigation (right stick + prefer unfilled) and D-pad quadrant jump
4. Implement camera pan + trigger zoom + nudge + L3 snap
5. Implement hold-to-fill (temp preview -> commit/reject) + cancel-on-movement
6. Implement autosave + load
7. Implement numbers-in-regions rendering with thresholds
8. Add generator presets A-D (export to puzzle format)
9. Add settings menu for preset/scale/colors
10. Add main menu (New Game / Continue / Gallery)
11. Add completion snapshot + gallery viewer
