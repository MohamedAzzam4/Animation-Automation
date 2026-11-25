# PHASE REPORT — Stylized 3D Character Animation (deterministic Godot prototype)

Branch: `experiment/stylized-3d` (2D renderer untouched, never merged to main)
Engine: Godot 4.7.2 stable, headless Xvfb + `--rendering-driver opengl3`
(software GL) + Movie Maker `--write-movie --fixed-fps 30`, FFmpeg H.264/AAC.
Character: AvatarSample_B (VRM 0.x, VRoid) via godot-vrm `e15199f9` + MToon.
Motion: Quaternius UAL 1 & 2 (CC0, Godot GLBs), runtime world-delta retarget.
Checkpoints: every phase committed and pushed to `Animation-Automation`.

## Phase status (all phases have evidence video + visual check + report)
| Phase | Deliverable | Status |
| --- | --- | --- |
| 0 | environment + Movie Maker pipeline | PASS |
| 1 | VRM/UAL inspection + `character_capabilities.json` + 6-view reel | PASS |
| 2 | retargeting: 16 clips, transitions, real root motion | PASS (7.5/10) |
| 3 | facial expressions (11 presets, 4 intensities, composites, gaze, blinks) | PASS (8.5/10) |
| 4 | lip-sync A (amplitude) vs B (phoneme viseme), German fixture | PASS (B wins) |
| 5 | interaction: chair, mug/book attach, door, 2-bone arm IK, camera track | PASS (w/ limitations) |
| 6 | 4 environments, yaw-relative cameras + room-bounds clamp | PASS (7-9/10) |
| 7 | pilot story "Ein unerwarteter Besuch" A2 de, 62.2 s, 3 scenes | PASS (7/10) |
| 8 | generalization: new story JSON, zero new GDScript | PASS (7/10) |
| 9 | final report, schema, prompt, bundle, deliverables | this document |

## Honest capability assessment (as demanded — no assumptions)

**Truly usable (production-quality for this prototype):**
- VRM import + MToon materials; blend-shape expressions with crossfades;
  VRM0 override semantics (viseme over expression, blink additive).
- Deterministic timeline compilation: same JSON + seed -> identical schedule;
  Movie Maker renders are pure functions of the frame number.
- Walk/retarget pipeline: real root motion (paths own XZ, walk plays in
  place), no moonwalk after adding turn segments.
- Sit/stand cycles aligned to furniture; door swing on schedule.
- Camera system: avatar/yaw-relative offsets + room-bounds clamp + push_in +
  smooth damping + walk target tracking.
- Subtitles in a fixed safe area + separate SRT; espeak-ng audio is cacheable
  and deterministic.

**Usable but not fully natural (documented approximations):**
- Retargeted gestures: shoulders/arms slightly stiff (rig proportion
  difference Quaternius->VRoid); stride slightly short.
- Procedural poses (wave/think/hold_book) via 2-bone IK: geometrically correct
  (verified numerically to ~1 cm) but elbow style is plain; no shoulder roll.
- Prop grip: mug/book ride the hand bone with a fixed offset — contact reads
  approximately right, not finger-accurate.
- Lip-sync Method B: phoneme->viseme with interpolated phoneme timing (no
  MBROLA/forced-alignment in sandbox); word boundaries exact, phoneme
  boundaries approximate. Method A (amplitude) kept as baseline.
- Physics-free hair/skirt: secondary bones follow parents rigidly
  (deterministic, but no simulation).

**Approximations (acceptable for stylized output):**
- Expressions worried/confused/thinking are composites of VRM0 presets
  (documented weights), not bespoke shapes.
- Environments are primitive-based stylized sets (no textures/lightmaps).
- espeak-ng German voice = free local TTS, disclosed; not human quality.

**Character does NOT support / not implemented:**
- Second character on screen (Ben never appears; story tells around it).
  The schedule format supports multiple avatars but the director drives one.
- Sitting on benches (park has no sit anchor in the catalog — validator
  rejects it; extendable by adding an anchor + clip mapping).
- Object hand-off between characters, door usage by the character (door opens
  by schedule, not by a push animation).
- Physically simulated cloth/hair, foot IK locking (feet follow hips height
  scaled by 0.958; minor foot-slide possible on long walks).

**Sandbox-blocked (worked around, disclosed):**
- No GPU: software GL (llvmpipe) at ~180-215 ms/frame; renders are slow but
  correct. GPU would be 10-30x faster.
- No paid APIs: Gemini TTS not used for the 3D pilot (quota protection);
  espeak-ng used instead and disclosed in `audio_manifest.json`.
- No Blender: everything (retarget, IK, environments) done in Godot runtime
  GDScript; import-side bone maps hand-authored.

**Needs external tools / future work:**
- True phoneme timing (Whisper word-level != phoneme-level): would need
  MBROLA or a forced aligner with phoneme output.
- Finger-accurate grasping: needs per-object grasp poses or physics.

**Not tested:** multi-avatar scenes, en-US/es-ES lip-sync maps (map tables
exist for German only), 4K/60fps, GPU rendering paths.

## 3D vs 2D evaluation (the experiment's core question)

**Did 3D reduce manual asset work? YES, clearly.**
- 2D: every expression/pose/camera framing was hand-drawn or hand-composited;
  the failed 2D experiments spent most effort on face-anchoring sprites to
  head positions, and portraits were per-character static art.
- 3D: ONE character model (15 MB VRM) + two CC0 animation libraries give
  ~90 animations, 56 face blend shapes, and unlimited camera angles with zero
  additional art. New expressions = weight tables; new shots = camera offsets.
  New story = JSON only (Phase 8 proved it: zero GDScript).

**Did 3D reduce face-alignment problems? YES, structurally.**
- 2D failure modes (wrong facial overlays, floating busts, mouth detached
  from face) are structurally impossible here: expressions are mesh blend
  shapes ON the face; visemes override the mouth per VRM0 semantics; blinks
  clamp additively. No 2D compositing layer exists to mis-align.
- Remaining face issues are of a different class (hair covering eyes at
  extreme head turns, close-up aliasing) — cosmetic, not structural.

**Where 2D was better:** pixel-perfect art direction, subtitle typography,
and render speed per frame (2D composites were cheaper than 3D shading).

**Verdict:** 3D wins for scalable language-video generation: one model +
catalog-driven animation covers unlimited stories with deterministic output.
The prototype is a working foundation, not yet a product (second character,
bench sitting, foot locking, phoneme-exact lipsync are the next four things
to build).

## Performance (llvmpipe, 1280x720@30)
- Phase 0 scene: 72 ms/frame. Character scenes: 162-215 ms/frame.
- 62 s pilot: ~40 min GPU render total (3 scenes) + ~4 min encode.
- Determinism: Movie Maker fixed fps + no RNG in render path (seeded RNG only
  for blink placement in the compiler, which is part of the schedule).

## Reproduce
```sh
git clone <Animation-Automation> && git switch experiment/stylized-3d
pip install -r requirements.txt   # numpy only for the compiler
# assets: godot3d/assets3d (checksummed in ASSETS3D.md), engine: Godot 4.7.2
sandbox3d/phase0_render.sh 1 && ... # per-phase scripts, see reports3d/
python3 sandbox3d/story_compiler.py sandbox3d/pilot_story.json out/pilot
```
