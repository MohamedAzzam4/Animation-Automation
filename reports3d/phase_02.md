# Phase 2 — Body animation retargeting (UAL -> VRM)

Status: **PASS** (with documented minor limitations)

## Method
Runtime **world-delta retarget** (`godot3d/retarget.gd`), no editor import magic:
for each mapped bone (topological order) `D = Wa_src * Wb_src^-1`,
`Wa_dst = D * Wb_dst`, solved back to avatar-local poses each frame.
- Full humanoid map incl. fingers/toes: UAL1 (Rigify `DEF-*`, 50 bones) and
  UAL2 (UE-style, 50 bones) -> VRM humanoid names.
- Hips translation: world-space delta scaled 0.958, **XZ locked** (world
  position owned by the deterministic `paths` track), Y keeps bob/sit/crouch.
- Deterministic crossfades (slerp/lerp over fixed frame counts).
- 6 procedural upper-body clips (wave/point/think/hold_book/turn_l/r) layered
  over the retargeted Idle base.

## Root causes found & fixed (the honest list)
1. First full render: character pitched 90 deg forward (face-down, floating).
   Cause: UAL rigs are Z-up under a `root` bone with a -90 deg X rest; the
   hips POSITION path had the world-basis conversion but the ROTATION chain
   seeded unmapped parents with identity. Fix: `src_parent_bind_q` carries the
   root bone's global rest rotation into the world chain.
2. `AnimationPlayer.seek()` with no assigned animation silently applies
   nothing (everything stayed at bind). Fix: assign `current_animation`
   before seeking; process mode MANUAL.
3. Sitting initially moved hips UP (+0.27 m): local-space hips delta applied
   as world delta. Fix: `src_root_basis * delta_local` conversion, then
   world-XZ lock, then avatar-parent basis inverse.

## Verification
- Headless probes: hips heights idle 0.833 / walk 0.874 / sitting 0.519 m
  (anatomically correct); no NaN; head world Z-axis stays exactly (0,0,1)
  at bind/idle/walk (facing preserved, verified numerically).
- **Root motion is real**: walk beat translates the avatar root 0 -> 2.2 m
  along +Z while the clip plays in place; no teleporting.
- Visual (VLM, 9-beat contact sheet): upright in all beats, grounded feet,
  natural stride with arm counter-swing, seated ON the chair (hips at seat
  height, knees bent, no through-seat clipping), no T-pose/backwards knees/
  detached limbs. Rating 7.5/10.
- Documented limitations (accepted): stride slightly small for leg length,
  arms a bit close to the body in idle/talking (proportion difference between
  Quaternius mannequin and VRoid rig), minor seat-edge contact imprecision.

## Clips verified working
UAL1: Idle, Walk, Sitting_Enter, Sitting_Idle, Sitting_Talking, Sitting_Exit,
Idle_Talking. UAL2: Yes, Idle_No, Idle_FoldArms.
Procedural: wave, point_right, think, hold_book, turn_left, turn_right.
Transitions verified: idle->walk->idle, stand->sit->sit-idle->sit-talk->stand.

## Evidence
`evidence3d/phase_02_body_animation.mp4` (46.6 s, 18 labeled beats),
`evidence3d/phase_02_contact_sheet.png`.

## Reproduce
```sh
sandbox3d/phase2_render.sh 1   # Movie Maker AVI
sandbox3d/phase2_render.sh 2   # encode + contact sheet
```
