# Phase 0 — Audit, Godot install, baseline

## Environment

| Item | Value |
| --- | --- |
| OS | Linux x86_64, kernel 5.10.134 (sandbox) |
| Python | 3.12.16 |
| FFmpeg | `/usr/bin/ffmpeg` (system) |
| Godot | **4.7.2.stable.official.ed1daf0bf** |
| Godot exe path | `godot_dist/Godot_v4.7.2-stable_linux.x86_64` (work machine); resolved at runtime via `GODOT_BIN` env or `--godot-path` |
| Godot source | Official https://godotengine.org/download/linux/ → https://downloads.godotengine.org/?version=4.7.2&flavor=stable&slug=linux.x86_64.zip (standard GDScript edition, NOT .NET/mono) |
| Display | No real GPU. Xvfb + Mesa llvmpipe (OpenGL 4.5 compat), Godot run with `--rendering-driver opengl3` |

## Skills status (required disclosure)

- **Ponytail skill: NOT INSTALLED** in this agent environment (checked `skills/` inventory).
  Following its documented minimum-working-solution principles instead: reuse existing code
  (audio/TTS/alignment reused from `lesson.py` via import), Godot built-ins over plugins
  (Sprite2D/Node2D/CanvasItem/Movie Maker only, no addons), fewest dependencies (no new pip
  requirements beyond what the repo already uses), no premature abstractions.
- **Godot skills: none installed.** No n8n, no Blender, no external DCC used.
- **VLM skill: installed and used** for real visual QC of every art sheet (descriptions below).
  This is how the "verify actual visible sprites" rule is honoured without human eyes.

## Commands run and results

```bash
# 1. Clone repo on feature branch
git clone https://github.com/MohamedAzzam4/language-video-workflow.git
git checkout -b feature/godot-renderer

# 2. Install Godot 4 stable from official site
curl -sL "https://downloads.godotengine.org/?version=4.7.2&flavor=stable&slug=linux.x86_64.zip" -o godot_linux.x86_64.zip
unzip godot_linux.x86_64.zip
godot_dist/Godot_v4.7.2-stable_linux.x86_64 --version
# -> 4.7.2.stable.official.ed1daf0bf

# 3. Godot launch proof on device (headless via Xvfb, llvmpipe GL)
Xvfb :99 -screen 0 1280x720x24 &
DISPLAY=:99 godot ... --path <smoke project> --rendering-driver opengl3 \
    --write-movie out.avi --fixed-fps 30 --quit-after 40
# -> "Movie Maker mode enabled, recording movie in 1280×720 @ 30 FPS"
# -> "30 frames at 30 FPS ... recorded in 00:00:01 (100% of real-time speed)"
# -> ffprobe out.avi: mjpeg 1280x720 30/1 + pcm_s16le  (validated)

# 4. Baseline: existing Python unit tests
python3 -m pytest test_lesson.py test_studio.py -q
# -> 10 passed in 7.79s

# 5. Baseline: existing offline demo render
python3 lesson.py --script example.json --demo --output ../baseline_output
# -> Exported ../baseline_output/video.mp4  (video.mp4, audio.wav, subtitles.srt, timeline.json)
#    copied to art/qa_baseline.mp4 as the frozen baseline
```

## Asset audit (art/qa/asset_audit.json + art/qa/contact_sheet.png)

All 17 files: **SHA-256 checksums match manifest.json exactly** (0 mismatches).

Programmatic findings + VLM visual QC findings:

| Group | Finding |
| --- | --- |
| `reference/*` | Clean canonical busts (head-to-hips), correct identities: Anna = copper-red bob, teal overshirt, white inner top; Ben = dark curly hair, short beard, mustard overshirt, white T-shirt. Use as identity truth + neutral body. |
| `design/*` | Turnaround/costume source sheets. Reference only (per manifest), not extracted. |
| `parts_sheets/*` | **NOT a usable rig.** VLM QC: paper-doll fragments (bald head, hollow wigs, detached sleeves, floating hands) scattered over heavy red/yellow/black glitch bands; large gray corrupted band bottom-right of Anna's sheet. Cutout rigging from these would damage identity. → documented gap, fallback used. |
| `faces/*` | **Golden asset.** 5 head-and-shoulder busts in one aligned row, same scale: gentle smile (neutral), laughing (happy), surprised "O", thinking (hand at chin), worried. Plus eye pairs, brows, ~11 mouth shapes (closed, smile, open smile, O, wide) and one larger head. Background has red/yellow glitch smears that must be cleaned out via alpha. |
| `poses/*_gestures` | Anna: 6 standing mid-thigh gesture figures (explain palms-up, wave, point, hand-on-chest, thinking, surprised whoa). Ben: 6 seated waist-up gestures (explain, wave, point, armchair-relaxed, thinking, startled whoa), some with visible table/chair. Red rim fringes + background debris to clean. |
| `poses/*_conversation` | Seated conversational poses per character (chin-on-hand, open-palm, clasped hands, armchair, profile) — good fallback/cafe seated set. |
| `backgrounds/*` | 4 clean 1672×941 RGB paintings: student room, station, café, golden-hour riverside park. 16:9 → direct 1280×720 downscale. |
| `storyboard/*` | Inspiration only. 4 panels matching the pilot story (room → station → café → park). NOT machine-usable; not used for rendering. |

## Minimum viable character strategy (decision)

Full cutout rig from `parts_sheets` is **not achievable without inventing art** (glitch damage,
hollow wigs, no tested joints) — exactly the false-claim trap the prompt forbids. Chosen strategy,
per the prompt's endorsed fallback:

1. **Composite bust compositor with swappable expressions** — the 5 aligned expression busts from
   `faces/` per character are the animated head+shoulders, swapped per turn `expression`.
2. **Eye/mouth overlay layers registered on a fixed canvas** — blink = pre-composited closed-eye
   variant; lipsync = small/open/wide mouth patches placed by template-matching at extraction
   time, so anchors are steady by construction.
3. **Gesture stickers** — wave/explain/point/whoa figures from `poses/` swapped in at matched head
   scale; nod/head_tilt implemented as deterministic transforms (bob/rotation) of the bust.
4. Seated poses kept as optional café variants.

Known gaps to document, not hide: paper-doll rig unused; glitch debris cleaned only via alpha
thresholds and region-limited crops (no repainting); Ben gesture cells may contain chair/table
fragments — each extracted cell is VLM-verified before use.

## Acceptance checklist

- [x] Godot 4 stable launches on device, version recorded (4.7.2.stable.official.ed1daf0bf)
- [x] Original pipeline offline tests pass (10/10) — no regression
- [x] Baseline offline render frozen (`art/qa_baseline.mp4`)
- [x] `art/qa/asset_audit.json` + `art/qa/contact_sheet.png` produced
- [x] Both characters visually verified against reference portraits (VLM QC above; identities match rule 4)
- [x] No API keys used or committed (demo path only; `.gitignore` unchanged, still ignores `.env*`, `output/`)

**Phase 0: PASS.**
