# Phase 7 — End-to-end pilot and UI

Ponytail check (skill not installed — principles applied): the studio keeps its
paste-JSON workflow with one added `<select>`; the render dispatch is one `renderer`
kwarg through the existing `lesson.render` (no forked pipeline); the last-run status
reads the manifest that the renderer already writes; no new dependencies.

## Lesson Studio integration

- `templates/studio.html`: "Renderer" select — *Still cards (original)* /
  *Godot (animated)*; per-run status line (engine version, frames, fps, seed or
  "still-card render"); Timeline download button appears only when the job produced
  `godot_timeline.json`; hint about optional scene_plan_v1 turn fields.
- `lesson_studio.py`: passes `renderer` through to `lesson.render`, includes it in the
  job identity hash, gates the extra downloads on file existence.
- Integration smoke (executed): studio test client → GET shows the select; POST with
  the pilot ticket + `renderer=godot` → 200, `video/mp4` (4,003,020 bytes), timeline
  with 4 scenes downloadable, "Animated render · Godot 4.7.2.stable…" status; POST
  with `renderer=pillow` → 200, still-card render (old path regression-free).

## Pilot execution (demo mode first, no secrets)

```bash
GODOT_BIN=... python lesson.py --script art/pack/pilot/lesson_ticket.json \
    --demo --renderer godot --output output/pilot_demo
# -> Exported output/pilot_demo/video.mp4
```

Outputs (all real files): `video.mp4` (563 frames, 18.8 s, H.264+AAC),
`audio.wav` (original demo track, unchanged), `subtitles.srt`, `godot_timeline.json`
(scenes: student_room@0, station@182, cafe@323, riverside_park@461 — transitions on
planned ticket boundaries, not per line), `script.json`, `render_manifest.json`.

Contact sheet QC (`art/qa/pilot_contact_sheet.png`, 8 frames, VLM): **PASS** —
identities consistent in all four scenes, scene order room → station → café → park
with clean transitions (no background mixing), German captions with correct umlauts
(fährt, Gleis vier, verdient, wunderschön), title bar and name chips present, no
broken visuals. Close-up frames intentionally hide the off-shot listener (Phase 4 fix).

The pilot visits exactly the planned story: planning in the student room, the platform
change at the station, cake at the café, golden hour in the park — only Anna and Ben.

## Real TTS

Not run: no Gemini key exists in this environment and live API calls are forbidden by
default. The real-voice path executes the identical imported code
(`speech_track` → `align_speech` → `add_pauses`); the owner can enable it locally with
`GODOT_BIN` + `GEMINI_API_KEY` and the same `--renderer godot` command without `--demo`.

## Acceptance checklist

- [x] Complete multi-scene demo MP4 + screenshot contact sheet
- [x] No secrets required for the demo (offline tone track, zero API calls)
- [x] Both characters visually consistent across scenes (VLM-verified)
- [x] Transitions correspond to the ticket's planned scene boundaries
- [x] No regressions in the old renderer (29/29 tests; pillow path re-rendered in the
      integration smoke)
- [x] Paste-JSON workflow preserved; preview (inline `<video>`) and downloads work

**Phase 7: PASS.**
