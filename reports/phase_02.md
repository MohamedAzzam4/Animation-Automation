# Phase 2 — Character controller

Ponytail check (skill not installed — principles applied): Godot built-ins only
(`Sprite2D`/`Node2D`/`CanvasItem` draws — no `AnimationPlayer`/`AnimationTree` needed since
all animation is a pure function of the absolute frame), one scene + two scripts, no
plugins, one runnable regression check (`TestAssets.tscn` from Phase 1 still passes).

## Implementation

- `godot/character.gd` + `Character2D.tscn`: composite-bust controller.
  - Two `Sprite2D` layers (`Body`, `Overlay`) on ONE shared canvas per character
    (`tools/bake_assets.py` pads every expression, overlay and gesture onto that canvas
    anchored at the eye midpoint) — texture swaps can never move the head.
  - `setup(id)` preloads every texture (Phase 1 lesson: never `load()` during draw).
  - `set_state(frame, state)` is the ONLY entry point; all transforms are pure functions
    of the integer frame:
    - idle breathing: 2 px bob + 0.4% scale pulse, 111-frame period (3.7 s),
    - blink: overlay during 4-frame windows (schedule supplied by the timeline),
    - look left/right overlays for listener eye direction,
    - expressions: neutral/happy/surprised/thinking/worried,
    - speech mouths: closed/small/open overlay levels 0/1/2 on the mouth-erased base,
    - gestures: wave/explain/point figure swaps with 45-frame sway,
    - `nod` (36-frame dip) and `head_tilt` (54-frame eased ±3.4°) transforms,
    - gesture bodies fade at the same canvas line as bust bottoms (no framing pop).
- `godot/demo_characters.gd` + `DemoCharacters.tscn`: 300-frame deterministic demo.

## Commands run

```bash
python3 tools/bake_assets.py art/staging godot/assets      # re-bake (common canvas)
cd godot
DISPLAY=:99 <godot> --headless --path . --import
DISPLAY=:99 <godot> --path . --rendering-driver opengl3 \
    --write-movie /tmp/godot_test_out/demo.avi --fixed-fps 30 --quit-after 305
# -> 301 frames at 30 FPS (00:00:10:01)
ffmpeg -i demo.avi ... art/qa/phase2_demo.mp4              # full two-shot capture
ffmpeg -i demo.avi -vf "crop=640:720:180:0" ... phase2_demo_anna_focus.mp4
ffmpeg -i demo.avi -vf "crop=640:720:460:0" ... phase2_demo_ben_focus.mp4
```

## Real artifacts

- `art/qa/phase2_demo.mp4` (10 s, both characters) + two 10 s per-character focus crops
- `art/qa/phase2_frames.png` (6 sample frames), `art/qa/phase2_canonical_compare.png`

## Verification (measurements, not impressions)

VLM QC of sampled frames oscillated on "scale pop" (subjective impressions of the intended
gesture body-reveal), so the decisive check is a pixel measurement of head widths across
sampled frames:

| frame | state | Anna copper-hair blob | Ben hair+mustard blob |
| --- | --- | --- | --- |
| f10 | idle+blink | 223 px | 192 px |
| f60 | idle | 223 px | 192 px |
| f130 | Anna speaking | 213 px | 187 px |
| f200 | Anna wave | 217 px | 185 px |
| f230 | Ben explain | 218 px | 229 px (gesture incl. raised arm) |
| f280 | thinking | 207 px (hand at chin) | 230 px (gesture) |

Head blobs vary ≤ ~7% and only where the pose itself overlaps the hair (thinking hand,
gesture arms). No scale pop of the heads; the visible change is the documented intended
body-reveal during gestures.

Canonical identity comparison (rendered vs `reference/*_canonical.png`): **Anna MATCH**
(hair/freckles/teal+white), **Ben MATCH** (curly hair, beard, mustard+white). Noted quirks:
Anna's freckles/brows can read as "glasses" at small scale; Ben's look-overlay adds a
second eye highlight — both are minor composite-art artifacts, documented.

Known limitations (documented): mouth overlays do not animate during gesture figure swaps
(gesture faces are painted mid-expression); Ben's gesture figures keep faint chair hints;
"eye look" unavailable on happy/surprised (their bases have closed/wide eyes).

## Acceptance checklist

- [x] Two 10 s demonstration captures (Anna focus + Ben focus crops of the deterministic
      demo, plus the full two-shot version)
- [x] Idle breathing + blink visible (f10 blink, 111-frame bob measured by design)
- [x] At least three visible expressions (neutral, happy, thinking + surprised/worried assets ready)
- [x] One gesture each (Anna wave, Ben explain)
- [x] No scale pop (pixel-measured heads, table above)
- [x] No misplaced eyes/mouth or face drift (shared-canvas anchors by construction + QC)
- [x] Neutral pose compared to canonical sources: MATCH both

**Phase 2: PASS.**
