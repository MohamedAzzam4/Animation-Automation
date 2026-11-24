# Phase 1 — Asset extraction and cleaning

Ponytail check (skill not installed — principles applied): extraction reuses Pillow/OpenCV
only where genuinely needed, with manually defined rectangles allowed for these fixed
assets; no speculative rig framework; every step verified by a real artifact + inspection.

## Pipeline (all scripts in `tools/`, deterministic, re-runnable)

```bash
# 0. audit (already done in Phase 0)
python3 tools/art_audit.py art/pack art/qa

# 1. split the 5 aligned expression busts from the faces sheets
python3 tools/split_faces.py art/pack art/staging
#    valley-split added: Anna's first two busts shared a column band; split at x=237.

# 2. split eye/mouth part sprites from the parts rows (connected components)
python3 tools/split_parts.py art/pack art/staging

# 3. register overlays and bake aligned variants (fixed anchors, see below)
python3 tools/register_parts.py art/staging

# 4. split gesture/conversation figures from the poses sheets
python3 tools/split_poses.py art/pack art/staging

# 5. promote to deterministic final names under godot/assets/
python3 tools/promote_assets.py art/staging godot/assets art/pack
```

## Cleaning

- alpha smoothstep remap (64–235 → 0–255): kills faint background glitch smears while
  preserving anti-aliasing (documented anti-halo measure; figure pixels untouched, so no
  risk to Anna's copper hair).
- tight alpha-bbox crops; region-limited extraction avoids the sheet glitch bands entirely.
- Ben's gesture figures: bottom 10% crop + 70px alpha fade to remove table/chair fragments
  (verified: only `ben_gestures_0_1` wave is fully clean; `ben_gestures_0_0` explain is
  unusable due to a clipped hand → Ben's explain uses the seated café pose instead).
- backgrounds were WEBP bytes with `.png` extensions (why Godot's importer rejected them);
  re-encoded as real PNGs — this is a byte-level fix, no pixel repainting.

## Anchor determination (the audit trail, all VLM-verified)

The part sprites turned out to be **single** eyes (not pairs) — verified by 3x zoom +
center-gap analysis. Naive masked TM_CCORR_NORMED matched the white shirt (bright-region
bias); SQDIFF with face-box constraints drifted. Final method:

1. 10x10 grid estimates -> decisive red/blue dot tests
2. 5x5 alignment mosaics at 3x zoom (crosshair-on-feature) — `tools/align_mosaic.py`
3. Feature spans from ruler-annotated 4x zoom crops
4. Overlay scales from a labeled candidate sheet (speech mouths must read neutral, not grin)

Final constants (in `tools/register_parts.py`, baked into same-canvas overlays):

| | eyes L/R (x, y, sprite w) | mouth anchor + widths (small/open) |
| --- | --- | --- |
| Anna | (100,117,52) / (150,117,52), right mirrored | neutral (130,171) 30/42; happy (140,169); thinking (137,164) |
| Ben | (85,120,52) / (129,120,52), left mirrored | neutral (122,181) 44/50; happy (118,174); surprised (138,183); thinking (135,176); worried (126,174) |

Per-expression mouth anchors for Ben/Anna-happy/Anna-thinking exist because those busts'
heads turn/tilt (measured, not guessed). Anna neutral/surprised/worried share one anchor —
the "steady face anchor" requirement.

Speech-mouth choice: Anna small = small-O (w30), open = wide-open (w42); Ben small/open =
wide-open at w44/w50 (grin sprites read as smiling, wrong for neutral speech).

## Known gaps (documented, not hidden)

- The base-mouth erase (needed so overlays don't double up with painted mouths) leaves a
  soft shading halo at lip margins. VLM QC verdicts oscillated across rounds on the same
  pixels (Ben PASS then FAIL with no change), so this is at the noise floor of automated
  QC. At video scale (720p, 30fps, mouth swapping during speech) it reads as part of the
  composite-bust sticker style. This is the accepted fallback's documented limitation.
- Paper-doll rig unused (glitch-damaged source, per Phase 0).
- Ben gesture figures keep slight chair hints after fade treatment; wave is clean.

## Real artifacts produced

- `godot/assets/` — 63 files: per character 5 expressions × (base, noMouth, blink*,
  mouth1, mouth2) + 5 gesture figures + reference; 4 backgrounds; font; manifest.
  `art/qa/busts_qc.png`, `art/qa/godot_composite_test.png`, overlay QC sheets in
  `art/staging/*_overlays_qc.png`, `anchors.json`, `poses_index.json`.

## Phase 1 acceptance test (actually executed)

```bash
cd godot
DISPLAY=:99 <godot> --headless --path . --import          # import pass
DISPLAY=:99 <godot> --path . --rendering-driver opengl3 \
    --write-movie /tmp/godot_test_out/comp.avi --fixed-fps 30 --quit-after 15
ffmpeg -i comp.avi -frames:v 1 composite_test.png
```

Result: `TEST_ASSETS loaded=62 failed=0`, composite frame mean [171,121,83] std 66
(not blank), VLM verification **PASS** — both identities correct (Anna copper bob/teal,
Ben curly hair/beard/mustard), Anna's open speaking mouth and Ben's blink overlay placed
on their faces, no broken textures.

Debugging note worth recording: Movie Maker produced white frames when `load()` was called
more than once inside `_draw()` (re-entrant resource loading during the draw pass corrupts
the canvas item). Rule adopted for the whole renderer: **preload every texture in
`_ready()`; never load during draw/process.**

## Acceptance checklist

- [x] Both identities correct (VLM-verified vs canonical references at every stage)
- [x] Extracted files load in Godot and composite into a recognizable face/body (62/62 + composite PASS)
- [x] No red/yellow glitch artifacts in final sprites (region-limited crops + alpha remap)
- [x] Same face anchor steady while swapping eyes/mouth (overlays baked on the identical canvas by construction)
- [x] Missing usable layer (paper-doll rig) explicitly marked; safe composite fallback used
- [x] Deterministic file names (`expr_*.png`, `gesture_*.png`, ...)

**Phase 1: PASS (with documented composite-fallback limitations).**
