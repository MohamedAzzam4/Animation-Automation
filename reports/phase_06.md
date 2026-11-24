# Phase 6 — Real offline video export

Ponytail check (skill not installed — principles applied): no new dependencies (ffmpeg
already required by the repo); the entire audio path is imported from lesson.py (one
whole-lesson TTS request, cached WAV, Whisper alignment — never re-generated per line);
the old renderer remains the default and fully selectable; caching keyed by content
hash; one regression check per change (29 tests + the live export below).

## Implementation

`godot_renderer.render_godot(story, output, ...)` — the Python-driven export:

1. Audio: `lesson.demo_track(turns)` offline, or `speech_track` + `align_speech` +
   `add_pauses` (identical calls to the pillow renderer).
2. Cache: sha256(ticket + seed + WAV) + renderer version + asset-tree hash. Same
   source → `"Reusing cached Godot render (source hash unchanged)."` (verified live).
3. Compile timeline (integer frames, seed 42) → `godot_timeline.json`; frozen ticket →
   `script.json`; SRT from the same ms timings as the old renderer.
4. Godot import pass (`--headless --import`) keeps the script/texture cache fresh —
   this guards against the stale-cache bug found in Phase 4.
5. Render: `godot --path godot --rendering-driver opengl3 --write-movie video.avi
   --fixed-fps 30 --quit-after N+10 -- --timeline <file>` under a PRIVATE Xvfb display
   (the `_Xvfb` helper brings its own display per render; no manual steps).
6. Mux: FFmpeg maps Godot's video + the original (frame-padded) WAV → H.264 CRF 20 +
   AAC 128k MP4, `-r 30 -t total_frames/30` (exact duration, faststart).
7. `render_manifest.json` records versions, seed, hashes, frame count.

`lesson.py` gained `--renderer {pillow,godot}` (default `pillow`; old behaviour
byte-for-byte unchanged — the only test change was widening one mock lambda's
signature).

## Acceptance run (exact commands and outputs)

```bash
GODOT_BIN=... python3 lesson.py --script art/pack/pilot/lesson_ticket.json \
    --demo --renderer godot --output /home/z/my-project/work/godot_export_test
# -> Exported .../video.mp4

ffprobe video.mp4
# codec h264 1280x720 30/1, nb_frames=563 (== timeline total_frames=563)
# codec aac, duration 18.767 s (== 563/30)
```

- Speaker highlight at exact frame boundaries (programmatic chip-colour check):
  - frame 42 (pause): both chips cream;
  - frame 44 (ben's turn starts at 43): ben chip accent, anna cream;
  - frame 183 (anna's turn starts at 182): anna accent, ben cream.
- Umlauts (zoomed crops, VLM-verified): "Wir **können** mit dem Zug…" caption and the
  title "Ein **überraschender** Nachmittag" render ö/ü as proper single characters
  (ß verified in Phase 3). No boxes, no decomposed diacritics.
- No dropped/duplicated frames: container frame count equals the compiled schedule.
- Cache: second run with identical ticket+WAV reused the render (hash match).

## Real artifacts

`/home/z/my-project/work/godot_export_test/`: video.mp4 (4 MB, 18.8 s, all 4 scenes:
student_room→station→cafe→riverside_park), audio.wav (original demo track, unchanged),
subtitles.srt, godot_timeline.json, script.json, render_manifest.json.

**Phase 6: PASS.**
