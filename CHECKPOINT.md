# Checkpoint policy

Every phase of the stylized-3D experiment is committed to the
`experiment/stylized-3d` branch and pushed to the checkpoint remote
`Animation-Automation` immediately, so a sandbox loss can never destroy
more than the current in-flight phase.

Pushed per phase:
- `godot3d/` project source (scenes, GDScript, addons config, asset manifests)
- `sandbox3d/` pipeline scripts (compiler, fixtures, render shell scripts)
- `reports3d/phase_XX.md` evidence report + PASS/PARTIAL/FAIL/BLOCKED status
- `evidence3d/` small MP4 evidence reels and contact sheets (no raw AVIs)

Never pushed: engine binaries, `.godot/` import caches, `output3d/` render
workdirs, secrets. Large third-party binaries are committed once
(`godot3d/assets3d/`, ~29 MB total, checksummed in `ASSETS3D.md`).

Restore: clone this repo, `git switch experiment/stylized-3d`, install
Godot 4.7.2, run `sandbox3d/` scripts (they use absolute sandbox paths
`/home/z/my-project/...` — adjust or recreate the same layout).
