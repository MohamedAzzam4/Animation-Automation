# Phase 3 — Lip sync from cached audio

Ponytail check (skill not installed — principles applied): loudness-driven 3-shape
open/close exactly as the phase allows (no phoneme claims); numpy-only DSP; eyes and
gestures remain composable (mouths are one overlay layer among blink/look, all on the
shared canvas); one regression check per change (unit tests + exact-frame inspection).

## Method (documented honestly)

`godot_renderer.py`:

- `audio_envelope(pcm)`: per-frame RMS of the cached 24 kHz mono WAV (the SAME audio the
  old renderer uses — one whole-lesson request, cached, never re-generated).
- `mouth_cues_for_turns(pcm, turns, intervals)`: for each turn, only that speaker's mouth
  may move and only inside the turn's aligned [start, end] interval. Per-turn adaptive
  thresholds from deterministic percentiles (floor = p10, peak = p97):
  level 2 (open) > floor + 0.62·span; level 1 (small) > floor + 0.22·span; else closed.
  Minimum 2-frame runs kill single-frame flicker. **This is amplitude-driven only — it is
  NOT phoneme or viseme alignment, and this report does not claim that.**
- Blinks are pre-scheduled at compile time with `random.Random(42)` (seeded — Godot side
  has zero randomness).
- `compile_timeline(...)` freezes everything into integer frame events (`timeline_v1`).

## Test audio

- A real German speech fixture was generated locally with the sandbox TTS skill
  (Anna 14.5 s + Ben 19.4 s; 24 kHz mono 16-bit, same format as lesson audio). These are
  TEST RECORDINGS for algorithm QC — not the lesson TTS; the pilot export itself still
  runs on the offline demo track with no keys.
- `dialogue_test.wav`: Anna 0–4.5 s, 0.8 s pause, Ben 5.3–11.3 s (11.3 s total).

## Acceptance run (exact commands)

```bash
python3 /home/z/my-project/scripts/phase3_test.py
# compiles the timeline, renders via:
#   godot --path godot --rendering-driver opengl3 --write-movie video.avi \
#       --fixed-fps 30 --quit-after 349 -- --timeline <timeline.json>
# muxes the ORIGINAL WAV (unchanged) -> video.mp4
# -> 340 frames at 30 FPS; audio stream untouched (ffmpeg -map 1:a)

python3 -m pytest test_godot_renderer.py test_lesson.py test_studio.py -q
# -> 27 passed (17 new + 10 original, no regressions)
```

## Exact-frame inspection (the acceptance criteria)

| frame | phase | timeline mouth level (anna) | VLM observation |
| --- | --- | --- | --- |
| f6 | speech start | 1 | Anna's mouth slightly open; Ben closed |
| f55 | mid-speech (loudest frame) | 2 | Anna's mouth wider open; Ben closed, idle |
| f147 | silence (pause) | 0 | both mouths closed |

Ben (listener) stays idle with closed mouth throughout Anna's turn; `ben` mouth runs
during Anna's speech: none (verified programmatically — cues only exist inside each
speaker's own interval). The caption bar shows the German text with correct `ß`
("heiße"); umlaut glyphs come from the same bundled Noto font the old renderer uses and
are verified visually in the Phase 6/7 pilot (whose turns contain ä/ö/ü).

## Real artifacts

- `art/qa/phase3_frames.png` (three exact frames)
- work dir: `lipsync_test/render/video.mp4` (11.3 s, H.264 + original WAV) + `timeline.json`

## Known limits

- Amplitude-driven 3 shapes only; true viseme lip shapes (more than open/small/closed)
  were deliberately not attempted — measurable improvement could not be demonstrated
  with available QC tooling, per the phase's "only if measurable" bar.
- Mouths do not animate during gesture figure swaps (painted gesture faces).
- On the demo tone track (offline pilot) the mouth pattern is mechanically regular; the
  pilot report says so explicitly instead of claiming speech-quality lipsync.

**Phase 3: PASS.**
