# Phase 4 — Environments + camera

Ponytail check (skill not installed — principles applied): backgrounds are the supplied
paintings only (no generic stock images, no external video-generation APIs); ambient
effects are Godot-native CanvasItem draws (no particles system, no runtime randomness —
phase tables were sampled once with `random.Random(42)` and baked as constants);
camera is a plain `Camera2D` driven per frame.

## Implementation

- `godot/ambient.gd` (reusable, optional: `effect` property, empty disables it):
  - `student_room` → dust motes drifting in window light (20 motes, sine drift)
  - `station` → slow cloud shadows sweeping the concourse (3 soft shadows, ~173 s cycle)
  - `cafe` → warm light breathing + rising steam wisps
  - `riverside_park` → golden-hour leaves falling on Lissajous paths (7 leaves)
  All positions are pure functions of the absolute frame + fixed phase constants.
- `godot/main.gd` camera presets (evaluated per frame from the turn's `camera` field):
  - `two_shot` (zoom 1.0), `close_anna` / `close_ben` (zoom 1.55 on the speaker),
    `establishing` (slow 1.0 → 1.05 push-in across the scene's duration, frame-exact).
  - The off-shot listener is hidden during close-ups so no face is ever cut by the
    frame edge (QC-driven fix).
  - Captions/title/name-chips live in a screen-space `CanvasLayer` — camera moves can
    never occlude or push them off-screen (safe area guaranteed by construction).
- Characters keep fixed left/right anchors (Anna 400, Ben 880) in every scene.

## Bugs found and fixed during this phase (with their regression evidence)

1. `draw_string` with `HORIZONTAL_ALIGNMENT_CENTER` and `width = -1` does NOT center
   (text starts at pos.x): captions were right-shifted and could touch the bar's right
   edge. Fixed by passing the real rect width; verified by pixel measurement
   (text columns 279–897 of 1184, centered, inside) and VLM re-check.
2. `ambient.gd` used `:=` inference from untyped arrays (`PHASE[i]`) — a parse error that
   left the ambient node unscripted and aborted `_process`. Fixed with explicit
   `: float =` types; `--check-only` clean afterwards.

## Acceptance run

```bash
python3 /home/z/my-project/scripts/phase4_render.py 1   # student_room, station, cafe, riverside_park
python3 /home/z/my-project/scripts/phase4_render.py 2   # + station_rerun for repeatability
# each scene: 10 s (339 frames) rendered via Movie Maker at 30 fps
```

- 4 ten-second scene outputs: `art/qa/phase4_{student_room,station,cafe,riverside_park}.mp4`
- VLM QC of 2 frames per scene (`art/qa/phase4_scenes.png`): **4/4 PASS** — consistent
  background per row, unstretched, captions centered and fully inside the bar in every
  frame, cafe close-up shows Anna's face fully with no cut faces, riverside zoom smooth
  without jitter, ambient movement visible in all four rows.
- Repeatability: `station` rendered twice from the same timeline → frame sha256 at
  f60/f200 identical (`585a46a2…`, `76f49d65…`) — **byte-identical frames**.
- Background AR: 1672×941 → 1280×720 (both ≈16:9, stretch factor 1.0006, invisible).

**Phase 4: PASS.**
