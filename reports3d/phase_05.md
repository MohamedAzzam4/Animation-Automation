# Phase 5 — Character/object/environment interaction

Status: **PASS** (with documented limitations)

## What was built
- `godot3d/director.gd` — the universal `interaction_v1` timeline player:
  paths (position), turns (yaw), body clip switching with crossfades, all
  facial layers (via FaceDriver), **object attachments** (hand mode with
  BoneAttachment3D + deterministic from->to tween, world mode with tween
  back), door swing segments, camera track (pos/target/fov/push_to/smooth),
  subtitles, fades, multi-scene switching (pilot), default character-relative
  camera fallback.
- `godot3d/env_builder.gd` — 5 procedural environments (test_room,
  student_room, hallway, cafe, park) with the anchored furniture the catalog
  promises (desk/chair/mug/book/door/window/bed/shelf/lamps/counter/trees/
  bench). Mug/book are spawned by the director from the schedule objects
  (no duplicates).

## Root causes found & fixed (the honest list)
1. Procedural clips used the STANDING Idle base while the character was
   seated -> slumped face-down pose over the table. Fix: procedural clips
   sample the last retargeted clip as their base (stance-aware).
2. UAL rigs are Z-up under a rotated `root` bone: hips POSITION delta needs a
   world-basis conversion (already fixed in Phase 2), and the ROTATION chain
   must seed unmapped parents with the root's world rest rotation (fixed in
   Phase 2, reused here).
3. Hand-attach tween used a feedback loop (`pos.lerp(pos, u)`) that converged
   back toward the off-hand start. Fix: explicit from->to lerp.
4. The door panel swung THROUGH the avatar and blocked the default camera.
   Fix: door opens to -72 deg (away), walk destination pulled back, and the
   schedule now carries a real camera track (room-side shot for the wave).
5. Static duplicate mug/book from the env builder vs. director-spawned ones.

## New capability: 2-bone arm IK (base-agnostic)
`ProcPoses.post_ik()` solves analytic 2-bone IK for the arms with manual
forward kinematics (the skeleton's own `get_bone_global_pose` is unreliable
mid-frame). Verified numerically: hand lands within 1 cm of the chest target
in a seated hold_book pose. Used for: think/drink (hand+attached mug to the
mouth), point_right, hold_book (both hands to chest), wave (hand beside head
+ wrist wag). Fingers relax to rest during held-object poses (removes UAL
finger-curl artifacts at close range).

## Verification (VLM across iterations)
- Sitting/standing on the chair: clean, no floating/clipping.
- Mug: attach fires at the exact scheduled frame, carried to the mouth
  region during the drink beat, tweened back to the table.
- Book: attached to the left hand at f624, held up to face height while
  examining (7/10 frame rating), tweened back.
- Door opens on schedule; wave beat visible from the room-side camera.
- No T-pose, no broken limbs, no slumped poses in any checked frame.

## Documented limitations
- Prop grip contact is approximate (mug reads slightly detached in some
  stills; offset-tuned to (0,-0.02,0.07) relative to the wrist bone).
- The wave still-frame can read as head-scratch; in motion the wrist wag
  helps. A dedicated wave-in-place clip would improve it.
- Chair seat contact is close but not pixel-perfect (seat 0.47 vs. seated
  hips 0.519).

## Evidence
`evidence3d/phase_05_interaction.mp4` (35.8 s, 15 labeled beats: idle -> walk
-> turn -> sit -> talk -> look/reach -> drink -> mug back -> book reach ->
examine -> book back -> stand -> door -> wave -> camera look), contact sheet.

## Reproduce
```sh
python3 sandbox3d/phase5_schedule.py
sandbox3d/phase5_render.sh 1 && sandbox3d/phase5_render.sh 2
```
