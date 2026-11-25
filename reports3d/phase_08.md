# Phase 8 — Generalization test

Status: **PASS** (7/10)

Second story "Ein Tag im Park" (A1 de, 33.6 s, park + cafe) rendered from a
NEW story JSON with **zero new GDScript**. The validator correctly rejected
two invalid capability uses on the first attempt (sit_idle without a chair
anchor in park; "laugh" used as an action) with the allowed list — exactly
the required fail-loud behavior; the story was fixed at the JSON level only.

Evidence: `evidence3d/Ein_Tag_im_Park_A1.mp4` + `evidence3d/gen_sheet.png`.
Verified (VLM): new locations/shots/captions work; character framed; minor
limitations: one background seam in cafe s2_3, minor sit alignment vs bench,
subtitle contrast on bright ground.

## Reproduce
```sh
python3 sandbox3d/story_compiler.py  # via compile_story_split driver
sandbox3d/pilot_render.sh 1 && sandbox3d/pilot_render.sh 2   # (path switched to output3d/general)
```
