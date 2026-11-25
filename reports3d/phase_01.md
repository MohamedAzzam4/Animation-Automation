# Phase 1 — Character inspection & capability catalog

Status: **PASS**

## What was verified
- **godot-vrm addon** (V-Sekai) pinned at commit `e15199f980064028bfa4fbee5e70dddb82dd55c3`
  (master 2026-07-08, "Update .import files for Godot 4.7"), MIT, vendored under
  `godot3d/addons/` together with its **Godot-MToon-Shader** dependency.
- **AvatarSample_B.vrm** imports cleanly: 126 bones, 3 meshes, 10+7+77 MToon
  surfaces (mtoon / mtoon_trans / mtoon_cutout shaders — no magenta/missing
  materials), face mesh carries 56 VRoid blend shapes.
- VRM 0.x (VRoidStudio-0.14.0 export). Blend shape presets found:
  `ALL_{Neutral,Angry,Fun,Joy,Sorrow,Surprised}`, `EYE_{Close,Close_L,Close_R,...}`,
  `MTH_{A,I,U,E,O,Up,Down,...}`, `HA_*` (teeth) — prefix `Face.M_F00_000_00_Fcl_`.
- Skeleton: clean humanoid names (Hips/Spine/Chest/UpperChest/Neck/Head/
  {Left,Right}{Shoulder,UpperArm,LowerArm,Hand,UpperLeg,LowerLeg,Foot,Toes} +
  fingers), LeftEye/RightEye present, spine chain rest rotations are IDENTITY
  (local axes == model axes → simple gaze math). Skirt/bust/hair secondary bones
  follow their parent bones deterministically (physics disabled by design).
- **UAL1.glb / UAL2.glb** (Quaternius, CC0): skeletons 53 / 65 bones.
  UAL1 rig = Blender-Rigify `DEF-*` names under a Z-up `root` bone
  (rest rotation −90° about X — important for retarget, see Phase 2).
  UAL2 rig = UE-style `pelvis/spine_0x/upperarm_l/...` names.
  All clips needed by the catalog exist: Idle, Walk, Sitting_{Enter,Idle,Exit},
  Sitting_Talking, Idle_Talking (UAL1); Yes, Idle_No, Idle_FoldArms (UAL2).

## Deliverables
- `godot3d/../output3d/phase1/character_capabilities.json` — machine-readable
  runtime dump (bones with parents/rest transforms, blend shapes, materials,
  animations with lengths/loop/track types).
- `evidence3d/phase_01_character_inspection.mp4` (15 s, 6 views:
  front / three-quarter / side / back / face close-up / full body, labeled).
- `evidence3d/phase_01_contact_sheet.png`.

## Visual check (VLM on contact sheet + frames)
Character intact full-body in all 6 views, correct clothing/hair/textures,
readable face in close-up (eyes, brows, mouth), shadows working, exposure
acceptable after tone-down (light 0.85, ambient 0.55, tonemap 0.85).
Camera orbit verified working (initial `%unique_name` lookup bug found and
fixed by switching to explicit relative node paths — root cause recorded).

## Notes / root causes fixed
1. First render had a static camera: `%Avatar`/`%ViewLabel` unique-name lookups
   fail when the scene is loaded as main scene headless → replaced with
   `get_node("../Avatar")` + lazy init.
2. GDScript `for k, v in dict` does not exist (parse error) → single-var loops.
3. Variant-inference parse errors on `lerp(float(d[k]), ...)` → explicit `: float`.

## Reproduce
```sh
sandbox3d/phase1_render.sh
```
