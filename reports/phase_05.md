# Phase 5 — Timeline compiler + JSON contract

Ponytail check (skill not installed — principles applied): the contract reuses the
existing ticket fields verbatim (title/language/level/turns/speaker/text/delivery/
pause_ms) and only ADDS optional visual fields; validation is one function with enums
as plain tuples; no schema library dependency.

## Contract: `scene_plan_v1` (input ticket)

- All original lesson.py fields are preserved untouched.
- Optional per-turn additions: `scene_id`, `expression`, `action`, `camera` (plus
  top-level `schema_version`, `seed`, `fps` as in the pilot ticket).
- Enums (validated BEFORE rendering, unknown values rejected with a friendly message
  listing the allowed values):
  - scenes: student_room, station, cafe, riverside_park
  - expressions: neutral, happy, surprised, thinking, worried
  - actions: idle, wave, explain, point, nod, head_tilt
  - cameras: two_shot, close_anna, close_ben, establishing
  - speakers: the lesson.py cast (anna/ben animated; maya/martin fall back to the old
    renderer with an explicit error explaining that)
- Old tickets without any visual fields pass and get defaults
  (student_room / neutral / idle / two_shot).

## Compiled output: `timeline_v1` (frame events)

`compile_timeline(story, pcm, intervals, seed)` — the audio alignment from lesson.py
(Whisper in real mode, demo tones offline) remains the single source of timing truth;
everything is converted to exact integer frame numbers at 30 fps:

- `scenes` (scene changes on planned boundaries), `turns` (start/end/next frame,
  expression, action, camera, ms timings for SRT), `mouths` (RLE per speaker),
  `blinks` (seeded schedule), `total_frames`, `seed`, `renderer_version`, fps/size.
- Validation happens before any rendering; the compiler refuses unknown enums,
  speaker mismatches, interval/turn count mismatches, and unsupported schema versions.

## Acceptance (executed)

```bash
python3 -m pytest test_godot_renderer.py test_lesson.py test_studio.py -q
# -> 29 passed (19 renderer + 10 original; includes: pilot ticket passes,
#    unknown scene/expression/action/camera/speaker rejected with allowed values,
#    identical compile in-process)
# cross-process determinism check (two separate python invocations):
# -> two independent compiles identical: True ['e36eb51d3ef950b8', 'e36eb51d3ef950b8']
```

Identical input ticket + WAV + seed 42 → byte-identical schedule JSON across separate
processes. The frozen artifacts land in each output folder as `script.json` (ticket)
and `godot_timeline.json` (compiled schedule) once Phase 6's export runs (implemented
next; the compiler itself is done here and already used by Phases 3–4 renders).

**Phase 5: PASS.**
