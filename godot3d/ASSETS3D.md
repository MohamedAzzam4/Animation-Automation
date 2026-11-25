# 3D Assets (experiment/stylized-3d)

All third-party assets used by the 3D renderer, with verified checksums.
No purchased assets, no paid APIs, no AI-generated character meshes, no Blender.

| File | Source | License | SHA-256 |
| --- | --- | --- | --- |
| `AvatarSample_B.vrm` | https://github.com/madjin/vrm-samples (raw) | VRM sample avatar, redistribution and use permitted per the vrm-samples repository terms (Pixiv VRM Consortium sample) | `4a271bd3b5a3d19e054fd113ee154635b72e7141f4a8ccbcdba3c7f9cea6ee8d` |
| `UAL1.glb` | Quaternius Universal Animation Library 1 (Standard, Godot build) https://quaternius.com/packs/animations.html | CC0 1.0 Universal | `1b7bf67866360665426bb99e4c71bd619f19b408453c24e30f0c3071601eee5c` |
| `UAL2.glb` | Quaternius Universal Animation Library 2 (Standard, Godot build) https://quaternius.com/packs/animations2.html | CC0 1.0 Universal | `0815dd05531cae9bc313fc9c0ba81330bc72f8e19ec45f73738e74ddc5796a43` |

Full license texts: `licenses/`. The UAL zips also ship Unity/Unreal variants and a
Female Mannequin mesh; only the Godot GLB animation sets are used here.

The `godot-vrm` addon (V-Sekai) is vendored under `godot3d/addons/godot-vrm`
with its own license file; the pinned version/commit is recorded in
`godot3d/addons/godot-vrm/VERSION` when installed (Phase 1).

Engine: Godot 4.7.2 stable (standard GDScript build, Linux x86_64),
rendered headless via Xvfb + `--rendering-driver opengl3` + Movie Maker.
