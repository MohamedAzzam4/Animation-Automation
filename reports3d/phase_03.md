# Phase 3 — Facial expression controller

Status: **PASS**

## What was built
`godot3d/face_driver.gd` — deterministic facial layer driven by absolute
frames:
- **11 catalog expressions** mapped to VRoid blend-shape composites
  (happy/smile=Joy, sad=Sorrow, angry=Angry, surprised=Surprised, relaxed=Fun,
  laugh=Joy+MouthA, worried=Sorrow@0.7+MouthSorrow, confused=Surprised@0.5+
  MouthDown, thinking=Joy@0.15+Blink_L@0.35+MouthUp — approximations
  documented in the catalog).
- 0.3 s **crossfades** between composites (per-shape weight blending).
- **Visemes** additive on the mouth (VRM0 override semantics respected).
- **Blinks**: 2-frame close, 5-frame open impulse.
- **Gaze**: world target -> avatar-local yaw/pitch, smoothed (lerp 0.25),
  distributed eyes (±15 deg yaw / ±9 pitch) -> head (0.62 of remainder,
  ±36/±22) -> neck (0.9 of rest, ±19/±11); premultiplied onto the animated
  bones after the body layer. Camera gaze supported.
- **Head nods** (sin, ramped 0.25 s) as additive pitch.

## Root cause found & fixed
First render showed near-zero expression change: the schedule's expression
segments were never wired to `set_expression()` (only visemes/blinks/gaze/nods
were read). The VLM saw only the neutral rest face (mis-read as subtle
smiles). Fix: `_apply_expression_schedule()` in `apply_frame()` picks the
latest active segment and triggers the crossfade on change. After the fix the
same reel rates 8.5/10.

## Verification (VLM on 10 full-res keyframes)
- happy@0.25 vs happy@1.0: intensity ramp visible (faint smile -> grin,
  eyes shut in happy arcs).
- sad / worried / concerned-nod read as one family, distinct from others.
- surprised: open "o" mouth + wider eyes. angry: furrowed brow + pressed
  mouth, clearly angry.
- laugh: eyes fully closed + open laughing mouth (blink+smile composite OK).
- thinking: half-lidded droopy eyes + smirk — distinct.
- gaze: look-left frame shows clear head+eye turn; surprised+turn shows turn.
- No face breakage, no double mouth, no melting features in any frame.

Documented limitation: low intensities (0.25-0.5) are subtle; hair bangs can
cover one eye during strong head turns (model hairstyle, not a defect).
Full-frame blink animation verified inside the MP4 (frame ~548: eyes closed
mid-laugh).

## Evidence
`evidence3d/phase_03_facial_expressions.mp4` (50.2 s, 26 labeled segments:
4-intensity happy, smile/sad/surprised/worried/confused/angry/laugh/thinking/
relaxed, simultaneous behaviors smile+blink, smile+look-away, surprise+turn,
concern+nod, gaze L/R/UP/DOWN/camera, blinks-only, return-to-neutral),
`evidence3d/phase_03_contact_sheet.png` (10 keyframes).

## Reproduce
```sh
python3 sandbox3d/phase3_schedule.py
sandbox3d/phase3_render.sh 1 && sandbox3d/phase3_render.sh 2
```
