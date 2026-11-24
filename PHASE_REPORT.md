# PHASE_REPORT — Deterministic Godot Language Video Engine

Repo: `language-video-workflow`, branch `feature/godot-renderer`
Environment: Linux x86_64 sandbox, Python 3.12.16, FFmpeg, Godot **4.7.2.stable.official.ed1daf0bf**
(official godotengine.org download, standard GDScript edition) rendered headless through
Xvfb + Mesa llvmpipe (OpenGL compatibility).

## Skills disclosure

- **Ponytail skill: NOT INSTALLED** in this agent environment. Per the handoff
  instructions, its documented minimum-working-solution principles were followed at
  every phase entry/exit: reuse of `lesson.py` audio/TTS/alignment code, Godot
  built-ins only (Sprite2D/Node2D/CanvasItem/Camera2D/Movie Maker, no plugins), no new
  pip requirements, and one runnable regression check per nontrivial change
  (`python -m pytest` — 29 tests, all passing).
- No Godot-specific skills installed. No n8n, no Blender, no external DCC.
- The installed **VLM skill** was used for real art QC (every extraction/alignment
  decision is VLM-verified; the audit trail is in the phase reports).

## Phase results

| Phase | Report | Verdict |
| --- | --- | --- |
| 0 Audit, Godot install, baseline | `reports/phase_00.md` | PASS — Godot 4.7.2 launches (Movie Maker smoke: 30 frames @ 100% real-time), original 10/10 tests pass, baseline demo video frozen, `art/qa/asset_audit.json` + contact sheet (all 17 pack checksums match). |
| 1 Asset extraction & cleaning | `reports/phase_01.md` | PASS — 63 cleaned assets on shared per-character canvases, VLM-verified anchors, 62/62 load in Godot, composite test PASS. Paper-doll rig rejected with documented evidence (glitch-damaged source); composite-bust fallback used as instructed. |
| 2 Character controller | `reports/phase_02.md` | PASS — `Character2D.tscn`/`character.gd`, all animation pure functions of the absolute frame; 10 s demo captures (full + per-character focus); head stability pixel-measured (≤7%, no scale pop); neutral poses MATCH canonical references. |
| 3 Lip sync from cached audio | `reports/phase_03.md` | PASS — loudness-driven 3-shape mouth cues from the cached WAV (explicitly NOT claimed as phoneme/viseme alignment); exact-frame inspection at speech start/mid/silence on a real-speech test recording; silence stays closed; listener idle; 17 new unit tests. |
| 4 Environments + camera | `reports/phase_04.md` | PASS — 4 scenes with deterministic ambient overlays (dust/clouds/glow/leaves), camera presets incl. establishing push-in; 4×10 s outputs, 2 repeatable frames per scene (byte-identical re-render), captions in a screen-space safe area. |
| 5 Timeline compiler + JSON contract | `reports/phase_05.md` | PASS — `scene_plan_v1` validated before rendering (friendly enum errors), old tickets default cleanly, identical input+WAV+seed → identical schedule JSON (verified across separate processes). |
| 6 Real offline video export | `reports/phase_06.md` | PASS — Python-driven Movie Maker + FFmpeg mux (H.264/AAC, exact 563 frames/18.767 s), speaker highlight verified at exact frame boundaries, umlauts (ö/ü/ß) correct, content-hash cache reuse verified, `--renderer godot` CLI with the old renderer untouched. |
| 7 End-to-end pilot + UI | `reports/phase_07.md` | PASS — pilot "Ein überraschender Nachmittag" (A2, demo mode, no secrets) rendered end-to-end: room → station → café → park, only Anna and Ben, scene changes on planned boundaries; Lesson Studio "Godot (animated)" choice + run status + timeline download; old renderer regression-free. |

## Working videos (all in `output/pilot_demo/`, copies in `download/language-video-godot/`)

- **`video.mp4`** — the complete multi-scene animated pilot (563 frames, 18.8 s, H.264+AAC,
  original audio track, SRT alongside).
- `phase2_demo.mp4` — 10 s character-controller demo (idle/blink/expressions/gestures).
- `phase3_lipsync.mp4` — real-speech lipsync test (11.3 s).
- `phase4_{student_room,station,cafe,riverside_park}.mp4` — 10 s per environment.
- `pilot_contact_sheet.png` — 8-frame pilot contact sheet (VLM-verified PASS).

## Test results

```bash
python -m pytest test_lesson.py test_studio.py test_godot_renderer.py -q
# 29 passed (10 original + 19 renderer) — no regressions in the old pipeline
```

Plus per-phase executable checks documented in each report (Movie Maker smoke,
Godot asset-load test, exact-frame inspections, cross-process determinism,
repeatability hash comparison, ffprobe stream validation, studio integration smoke).

## Unmet criteria / honest limitations

1. **Full cutout rig was not built.** The `parts_sheets` are glitch-damaged paper-doll
   fragments (hollow wigs, clipped hands, corrupted bands); rigging them would have
   required inventing art. The prompt's sanctioned fallback (quality-checked composite
   busts + eye/mouth overlays) was used and documented everywhere.
2. **Lipsync is amplitude-driven 3 shapes** (closed/small/open) — by design, per the
   phase's allowance; no phoneme or viseme claims are made. On the demo tone track the
   mouth pattern is mechanically regular; quality was validated on a real-speech test
   recording instead.
3. **Gesture faces don't animate mouths** during the ~2.4 s gesture windows, and Ben's
   gesture figures retain faint chair hints (fade-treated). Ben's `point`/`whoa` and
   Anna's `whoa` were dropped after QC (documented in phase 2) — the pilot only needs
   wave/explain + nod/head_tilt transforms.
4. **Real TTS run not performed** — no Gemini key exists in this environment and live
   API calls were forbidden by default. The real-voice path runs the exact same code
   (speech_track → align_speech → add_pauses is imported verbatim from `lesson.py`);
   the owner can run it by supplying `GEMINI_API_KEY` locally.
5. The base-mouth erase leaves a soft shading halo at lip margins (documented; VLM
   verdicts on the same pixels oscillated across rounds, so this is at the QC noise
   floor; at video scale it reads as part of the composite-bust style).
6. Godot was rendered through Mesa llvmpipe (software GL) — real-time speed ~50–100%,
   fine for offline Movie Maker exports; a GPU machine will be faster.

## Determinism statement

Ticket + WAV + seed 42 → identical `timeline_v1` JSON (cross-process verified) and
byte-identical frame samples on re-render (sha256-compared). All Godot-side animation
is a pure function of the integer frame counter; there is no runtime randomness, and
blinks are pre-scheduled by seeded Python. Versions are recorded in
`render_manifest.json` (renderer 1, Godot version, asset-tree hash, source hash).
