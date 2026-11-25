# Phase 4 — Lip-sync: amplitude vs phoneme-viseme

Status: **PASS** (Method B recommended; Method A kept as baseline)

## Fixture (free, local, disclosed)
- German test text (A/E/I/O/U + M/B/P + F/V + Ö/Ü + CH/SCH coverage):
  "Guten Tag! Ich übe heute die Vokale: a, e, i, o, u. Mama backt Pizza.
  Der Vater fährt sehr schnell. Fünf kleine Töchter möchten Bücher lesen.
  Ich lache in der Schule." — **espeak-ng 1.52.0** `de` voice, free local TTS
  (no paid API; Gemini TTS not used to protect quota).
- 31 words, 30.67 s, 920 frames @30 fps. **Word boundaries are EXACT**
  (each word synthesized separately and concatenated with fixed gaps).
- Phoneme boundaries: espeak-ng IPA + static German duration-weight table —
  a documented **approximation** (no MBROLA/forced-aligner phoneme timings in
  this sandbox; Whisper gives word-level, not phoneme-level, timestamps).

## Method A — amplitude (baseline)
RMS envelope per frame (floor p15, peak p97) -> 3 levels: closed / E@0.40 /
A@0.75, min-run merge. 115 mouth runs.

## Method B — phoneme -> viseme (recommended)
espeak IPA -> German viseme map (a->A, e->E, i->I, o->O, u->U, ö->O@0.5,
ü->U@0.5, bilabials closed, fricatives E/U approximations) -> VRoid MTH_*
blend shapes, additive over expressions (VRM0 override semantics), 2-frame
attack ramps, same-shape neighbour merging. 59 merged visemes.

## Verification
- **Timing evidence**: per-frame driver CSV logs for both methods
  (`amplitude_driver_log.csv`, `viseme_driver_log.csv`) — mouth state matches
  the word timeline (e.g. word "Guten" frames 0-25: u-viseme at frames 4-13).
- **Visual (VLM, full-res mouth crops at 5 divergent mid-viseme moments)**:
  Method B shows visibly ROUNDED/pursed U+O shapes (Guten/uebe/Vokale) and
  narrow I slits (i/Pizza) while Method A at the same frames shows closed or
  flat mouths — "viseme method produces distinct mouth shapes, not just
  openness: YES, confidence ~85%". Method A confirmed openness-only.
- Audio muxed into both reels (AAC 128k) and the side-by-side comparison.
- Honest methodology note: the first comparison attempt sampled frames at
  viseme attack transients (2-frame ramp) and was inconclusive; re-sampling
  mid-viseme gave the conclusive result above. Evidence image records both
  methods at the same 5 frames.

## Conclusion
Method B (phoneme visemes) is visibly better than amplitude and is used for
the pilot. Weaknesses: I-viseme contrast is subtle at distance; phoneme
timing is approximate. No face breakage in either method.

## Evidence
- `phase_04_amplitude_lipsync.mp4` (Method A + audio)
- `phase_04_viseme_lipsync.mp4` (Method B + audio... no: silent visual + audio muxed)
- `phase_04_comparison_side_by_side.mp4` (A|B same timeline + audio)
- `phase_04_mouth_comparison.png` (5 divergent moments, A vs B crops)
- `phase_04_contact_sheet.png`
- `fixture.wav`, `phoneme_schedule.json`, `viseme_schedule.json`,
  `amplitude_schedule.json`, both driver CSV logs

## Reproduce
```sh
python3 sandbox3d/phase4_fixture.py
sandbox3d/phase4_render.sh 1 && sandbox3d/phase4_render.sh 2 && sandbox3d/phase4_render.sh 3
```
