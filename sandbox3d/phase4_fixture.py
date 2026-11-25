#!/usr/bin/env python3
"""Phase 4: German speech fixture + two lip-sync schedules.

Fixture: espeak-ng (free local TTS, German 'de' voice) synthesizes each word
separately; word WAVs are concatenated with fixed gaps -> word boundaries are
EXACT on the timeline. Per word, espeak-ng --ipa gives the German phoneme
sequence; phoneme boundaries are interpolated inside the word interval with a
static German duration-weight table. This is NOT true forced alignment and is
documented as an approximation (no MBROLA phoneme timing in this sandbox).

Method A (baseline): RMS amplitude envelope of the same audio -> 3 mouth levels.
Method B (advanced): phoneme->viseme mapping table -> per-frame MTH weights.

Outputs (in output3d/phase4/): fixture.wav, phoneme_schedule.json,
viseme_schedule.json, amplitude_schedule.json, fixture_text.txt
"""
import json
import subprocess
import sys
import unicodedata
import wave
from pathlib import Path

import numpy as np

FPS = 30
RATE = 22050  # espeak-ng default output rate for -w
GAP_WORD = 90  # ms between words
GAP_SENT = 320  # ms between sentences

TEXT = ("Guten Tag! Ich übe heute die Vokale: a, e, i, o, u. "
        "Mama backt Pizza. Der Vater fährt sehr schnell. "
        "Fünf kleine Töchter möchten Bücher lesen. Ich lache in der Schule.")

OUT = Path(sys.argv[1] if len(sys.argv) > 1 else "/home/z/my-project/work/language-video-workflow/output3d/phase4")
OUT.mkdir(parents=True, exist_ok=True)

# German phoneme duration weights (ms) — static table, approximation
DUR = {
    "a": 80, "aː": 130, "eː": 125, "ɛ": 80, "ɛː": 120, "ə": 55,
    "i": 80, "iː": 125, "ɪ": 80, "o": 80, "oː": 125, "ɔ": 80,
    "u": 80, "uː": 125, "ʊ": 80, "øː": 120, "œ": 80, "y": 80, "yː": 120, "ʏ": 80,
    "aɪ": 170, "aʊ": 170, "ɔʏ": 170, "aɛ": 170,
    "m": 70, "n": 70, "ŋ": 70, "l": 65, "ʀ": 65, "ʁ": 65, "r": 60, "ɐ": 60,
    "f": 80, "v": 70, "s": 80, "z": 75, "ʃ": 85, "ʒ": 80, "ç": 75, "x": 75, "h": 55,
    "p": 55, "b": 55, "t": 50, "d": 55, "k": 55, "g": 60, "tʃ": 90, "p͡f": 100,
    "ʔ": 30, "j": 55,
}

# IPA -> (viseme shape, weight). Missing = silence/closed.
VISEME = {
    "a": ("A", 1.0), "aː": ("A", 1.0), "ɑ": ("A", 1.0), "ã": ("A", 0.9),
    "eː": ("E", 0.75), "ɛ": ("E", 0.75), "ɛː": ("E", 0.8), "ə": ("E", 0.45),
    "iː": ("I", 0.75), "ɪ": ("I", 0.7), "i": ("I", 0.75),
    "oː": ("O", 0.9), "ɔ": ("O", 0.85), "o": ("O", 0.9),
    "uː": ("U", 0.9), "ʊ": ("U", 0.85), "u": ("U", 0.9),
    "øː": ("O", 0.5), "œ": ("O", 0.45),       # ö approximation
    "yː": ("U", 0.5), "ʏ": ("U", 0.45), "y": ("U", 0.5),   # ü approximation
    "f": ("U", 0.3), "v": ("U", 0.3),          # approx lower-lip
    "s": ("E", 0.45), "z": ("E", 0.4), "ʃ": ("E", 0.5), "ʒ": ("E", 0.5),
    "ç": ("E", 0.3), "x": ("E", 0.35), "h": ("E", 0.25),   # German CH approx
    "n": ("E", 0.2), "ŋ": ("E", 0.2), "l": ("E", 0.25), "ʀ": ("E", 0.25),
    "ʁ": ("E", 0.25), "r": ("E", 0.2), "ɐ": ("E", 0.3),
    "t": ("E", 0.15), "d": ("E", 0.15), "k": ("E", 0.15), "g": ("E", 0.2),
    "j": ("I", 0.4),
    "p": (None, 0.0), "b": (None, 0.0), "m": (None, 0.0),  # bilabial: closed
    "ʔ": (None, 0.0), "ɡ": ("E", 0.2),
}


def espeak(args: list, stdin_text: str = None) -> str:
    r = subprocess.run(["espeak-ng"] + args, input=stdin_text,
                       capture_output=True, text=True, check=True)
    return r.stdout


def read_wav(path: Path) -> np.ndarray:
    with wave.open(str(path), "rb") as w:
        rate = w.getframerate()
        data = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
    return rate, data.astype(np.float32) / 32768.0


def write_wav(path: Path, rate: int, samples: np.ndarray) -> None:
    data = (np.clip(samples, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setparams((1, 2, rate, 0, "NONE", "not compressed"))
        w.writeframesraw(data.tobytes())


def split_sentences(text: str):
    out = []
    for s in text.replace(":", ": ").split(". "):
        s = s.strip().rstrip(".")
        if s:
            out.append(s)
    return out


# ---- 1. synthesize word by word (exact word boundaries) ----
events = []          # {word, phonemes, start_ms, end_ms}
chunks = []          # (samples, start_ms)
t_ms = 0
sentences = split_sentences(TEXT)
for si, sent in enumerate(sentences):
    for wi, word in enumerate(sent.split()):
        w_clean = word.strip(",!??")
        if not w_clean:
            continue
        wav = OUT / "_w.wav"
        subprocess.run(["espeak-ng", "-v", "de", "-s", "140", "-a", "180",
                        "-w", str(wav), w_clean], check=True,
                       capture_output=True)
        rate, samples = read_wav(wav)
        assert rate == RATE, f"rate {rate}"
        dur_ms = int(len(samples) / rate * 1000)
        chunks.append((samples, t_ms))
        # phonemes via IPA
        ipa = espeak(["-q", "--ipa", "-v", "de", "-s", "140", w_clean]).strip()
        events.append({"word": w_clean, "ipa": ipa,
                       "start_ms": t_ms, "end_ms": t_ms + dur_ms})
        t_ms += dur_ms + GAP_WORD
    t_ms += GAP_SENT - GAP_WORD  # extra sentence gap

# concatenate
total_ms = t_ms + 400
total = np.zeros(int(total_ms / 1000 * RATE) + RATE // 10)
for samples, start in chunks:
    i0 = int(start / 1000 * RATE)
    total[i0:i0 + len(samples)] += samples
peak = np.abs(total).max()
if peak > 0.99:
    total *= 0.99 / peak
write_wav(OUT / "fixture.wav", RATE, total)
(OUT / "fixture_text.txt").write_text(TEXT, encoding="utf-8")

# ---- 2. phoneme schedule (method B core) ----
phonemes = []
for ev in events:
    dur_total = ev["end_ms"] - ev["start_ms"]
    # parse IPA: strip stress/tie marks, group digraphs
    ipa = unicodedata.normalize("NFC", ev["ipa"]).replace("ˈ", "").replace("ˌ", "").replace("‿", "")
    ipa = ipa.replace("t͡ʃ", "tʃ").replace("p͡f", "pf").replace("a͡ɪ", "aɪ").replace("a͡ʊ", "aʊ").replace("ɔ͡ʏ", "ɔʏ")
    ph_list = []
    i = 0
    two = ["aɪ", "aʊ", "ɔʏ", "tʃ", "p͡f", "pf", "aɛ"]
    while i < len(ipa):
        matched = False
        for t2 in two:
            if ipa.startswith(t2, i):
                ph_list.append(t2)
                i += len(t2)
                matched = True
                break
        if not matched:
            ch = ipa[i]
            if ch.isalnum() or ch in "əɛɪɔʊøœʏŋçʃʒɐʁʀʔː":
                ph_list.append(ch)
            i += 1
    # durations: normalize table weights to the real word duration
    # merge length marks into the previous phoneme (u + ː -> uː)
    ph_merged = []
    for p in ph_list:
        if p == "ː" and ph_merged:
            ph_merged[-1] = ph_merged[-1] + "ː"
        else:
            ph_merged.append(p)
    ph_merged = ["ɡ" if p == "ɡ" else p for p in ph_merged]
    weights = [DUR.get(p, 60) for p in ph_merged]
    if not weights:
        continue
    scale = dur_total / sum(weights)
    pos = ev["start_ms"]
    for p, w in zip(ph_merged, weights):
        d = w * scale
        phonemes.append({"phoneme": p, "start_ms": int(pos), "end_ms": int(pos + d),
                         "word": ev["word"]})
        pos += d

json.dump({"rate": RATE, "fps": FPS, "text": TEXT,
           "words": events, "phonemes": phonemes,
           "total_ms": total_ms,
           "source": "espeak-ng de voice (free local TTS); word boundaries exact "
                     "(per-word synthesis), phoneme boundaries interpolated with a "
                     "static German duration table (approximation, no MBROLA in sandbox)"},
          open(OUT / "phoneme_schedule.json", "w"), indent=1, ensure_ascii=False)

# ---- 3. viseme schedule (method B) ----
visemes = []
for ph in phonemes:
    shape_w = VISEME.get(ph["phoneme"])
    if shape_w and shape_w[0]:
        visemes.append({"shape": shape_w[0].lower(), "weight": shape_w[1],
                        "start_frame": int(ph["start_ms"] * FPS / 1000),
                        "end_frame": max(int(ph["start_ms"] * FPS / 1000) + 1,
                                         int(ph["end_ms"] * FPS / 1000)),
                        "phoneme": ph["phoneme"], "word": ph["word"]})
# merge same-shape neighbours (avoid flicker)
merged = []
for v in visemes:
    if merged and merged[-1]["shape"] == v["shape"] and \
            v["start_frame"] - merged[-1]["end_frame"] <= 1:
        merged[-1]["end_frame"] = v["end_frame"]
    else:
        merged.append(dict(v))

json.dump({"fps": FPS, "total_frames": int(total_ms * FPS / 1000),
           "expressions": [{"start_frame": 0, "end_frame": int(total_ms * FPS / 1000),
                            "name": "neutral", "intensity": 0.0, "label": "viseme_lipsync"}],
           "blinks": [], "visemes": merged, "gaze": [], "head_nod": [],
           "method": "phoneme->viseme (German IPA map, espeak G2P)"},
          open(OUT / "viseme_schedule.json", "w"), indent=1, ensure_ascii=False)

# ---- 4. amplitude schedule (method A) ----
n_frames = int(total_ms * FPS / 1000)
samples_per_frame = RATE // FPS
pad = n_frames * samples_per_frame - len(total)
if pad > 0:
    total_p = np.concatenate([total, np.zeros(pad)])
else:
    total_p = total[:n_frames * samples_per_frame]
frames = total_p.reshape(n_frames, samples_per_frame)
rms = np.sqrt((frames ** 2).mean(axis=1))
floor = float(np.percentile(rms, 15))
peak_r = float(np.percentile(rms, 97))
span = max(peak_r - floor, 1e-4)
vis = []
for f in range(n_frames):
    v = (rms[f] - floor) / span
    if v < 0.25:
        continue  # closed mouth
    elif v < 0.6:
        vis.append({"shape": "e", "weight": 0.4, "start_frame": f, "end_frame": f + 1})
    else:
        vis.append({"shape": "a", "weight": 0.75, "start_frame": f, "end_frame": f + 1})
# min-run merge (2 frames) like the 2D renderer
def min_run_merge(items, min_len=2):
    # group consecutive same-shape runs
    out = []
    for v in items:
        if out and out[-1]["shape"] == v["shape"] and v["start_frame"] - out[-1]["end_frame"] <= 1:
            out[-1]["end_frame"] = v["end_frame"]
        else:
            out.append(dict(v))
    # drop 1-frame runs by extending neighbours
    cleaned = []
    i = 0
    while i < len(out):
        cur = out[i]
        if cur["end_frame"] - cur["start_frame"] < min_len and 0 < i < len(out) - 1:
            prev, nxt = out[i - 1], out[i + 1]
            if prev["shape"] == nxt["shape"]:
                prev["end_frame"] = nxt["end_frame"]
                i += 2
                continue
        cleaned.append(cur)
        i += 1
    return cleaned

json.dump({"fps": FPS, "total_frames": n_frames,
           "expressions": [{"start_frame": 0, "end_frame": n_frames,
                            "name": "neutral", "intensity": 0.0, "label": "amplitude_lipsync"}],
           "blinks": [], "visemes": min_run_merge(vis), "gaze": [], "head_nod": [],
           "method": "RMS amplitude envelope -> 3 levels (closed/E0.4/A0.75), floor p15 peak p97"},
          open(OUT / "amplitude_schedule.json", "w"), indent=1, ensure_ascii=False)

print(f"fixture: {total_ms/1000:.2f}s, {len(events)} words, {len(phonemes)} phonemes, "
      f"{len(merged)} merged visemes | amplitude runs: {len(vis)}")
