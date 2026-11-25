# Phase 0 — Environment (re-verification after sandbox loss)

Status: **PASS**

Date: 2026-11-25. Godot 4.7.2 stable (standard build), re-downloaded after the
sandbox recycle wiped `/home/z/tools`; now stored persistently under
`work/tools/godot/` inside the project and referenced from all scripts.

## Checks
- CPU software rendering path: Xvfb + `--rendering-driver opengl3` works
  (llvmpipe; GPU render time 10.9 s for 150 frames ≈ 72 ms/frame — acceptable
  for offline Movie Maker rendering).
- Movie Maker: `--write-movie phase0.avi --fixed-fps 30 --quit-after 150`
  produced exactly 150 frames; FFmpeg mux to H.264 1280×720 @30 (5.000 s).
- Scene: floor + 3 primitives + wall, DirectionalLight3D with shadows,
  ProceduralSky, deterministic scripted camera orbit (pure function of frame
  number under fixed delta).
- Visual check (VLM on frames 15/75/135): all geometry present, soft shadows
  visible, camera orbit confirmed, no missing textures, no z-fighting, no
  floating geometry. Minor: wall slightly overexposed (accepted for a
  placeholder scene, not used in final environments).

## Evidence
- `evidence3d/phase_00_environment.mp4` (5 s)
- Determinism: camera path is `_a = 0.22 * frame / 30`; same binary + scene
  re-render is frame-identical (Movie Maker fixed fps, no RNG, no physics).

## Reproduce
```sh
sandbox3d/phase0_render.sh            # renders 150 frames -> MP4 + ffprobe
```
