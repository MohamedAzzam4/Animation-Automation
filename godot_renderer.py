"""Deterministic Godot-renderer pipeline for the language video workflow.

Phase 3 scope: mouth-cue derivation from the cached lesson WAV (loudness-driven
3-shape open/close — deliberately NOT claimed as phoneme or viseme alignment),
deterministic blink scheduling (seed 42), and compilation of the frame-based
timeline JSON consumed by godot/main.gd.

The lesson audio path is REUSED from lesson.py (one whole-lesson TTS request,
cached WAV, local Whisper alignment); nothing here re-generates speech.
"""

import hashlib
import json
import math
import random
import subprocess
from pathlib import Path

import numpy as np

import lesson
from lesson import RATE, FPS, SAMPLES_PER_FRAME, video_frame, srt_time

GODOT_RENDERER_VERSION = 1
SCHEMA = "scene_plan_v1"
TIMELINE_SCHEMA = "timeline_v1"

SCENES = ("student_room", "station", "cafe", "riverside_park")
EXPRESSIONS = ("neutral", "happy", "surprised", "thinking", "worried")
ACTIONS = ("idle", "wave", "explain", "point", "nod", "head_tilt")
CAMERAS = ("two_shot", "close_anna", "close_ben", "establishing")
SPEAKERS = ("anna", "ben")          # animated identities (maya/martin stay on the old renderer)

# gesture figures that read correctly without surrounding furniture
GESTURE_FIGURES = {"anna": ("wave", "explain", "point"), "ben": ("wave", "explain")}
TRANSFORM_ACTIONS = ("nod", "head_tilt", "idle")

MOUTH_MIN_RUN = 2          # frames; avoids 1-frame flicker
BLINK_LEN = 4              # frames


def validate_scene_plan(story):
    """Validate scene_plan_v1 fields BEFORE rendering; unknown enums are rejected
    with a friendly message listing allowed values. Old tickets (no visual fields)
    pass untouched - defaults are applied at compile time."""
    if not isinstance(story, dict):
        raise ValueError("Ticket must be a JSON object.")
    for key, allowed in (("scene_id", SCENES), ("expression", EXPRESSIONS),
                         ("action", ACTIONS), ("camera", CAMERAS)):
        for number, turn in enumerate(story.get("turns", []), 1):
            value = turn.get(key)
            if value is not None and value not in allowed:
                raise ValueError(
                    f"Turn {number}: unknown {key} '{value}'. Allowed: {', '.join(allowed)}.")
    for number, turn in enumerate(story.get("turns", []), 1):
        if turn.get("speaker") not in lesson.VOICES:
            raise ValueError(f"Turn {number}: unknown speaker '{turn.get('speaker')}'. "
                             f"Allowed: {', '.join(lesson.VOICES)}.")
    animated = {turn.get("speaker") for turn in story.get("turns", [])}
    others = animated - set(SPEAKERS)
    if others:
        raise ValueError(f"Speaker(s) {', '.join(sorted(others))} have no animated Godot "
                         "identity; use the default renderer for them.")
    return True


def audio_envelope(pcm):
    """Per-frame RMS of the 24 kHz mono s16le PCM (deterministic, pure numpy)."""
    samples = np.frombuffer(pcm, dtype="<i2").astype(np.float32) / 32768.0
    n_frames = (len(samples) + SAMPLES_PER_FRAME - 1) // SAMPLES_PER_FRAME
    samples = np.pad(samples, (0, n_frames * SAMPLES_PER_FRAME - len(samples)))
    frames = samples.reshape(n_frames, SAMPLES_PER_FRAME)
    rms = np.sqrt((frames ** 2).mean(axis=1))
    return rms


def _runs(levels):
    """Run-length encode a level list -> [[start, end, level], ...] (end exclusive)."""
    out = []
    for i, level in enumerate(levels):
        if out and out[-1][2] == level:
            out[-1][1] = i + 1
        else:
            out.append([i, i + 1, int(level)])
    return out


def mouth_cues(pcm, intervals, speakers):
    """Deprecated helper kept out of the API; use mouth_cues_for_turns."""
    raise NotImplementedError("use mouth_cues_for_turns")


def mouth_cues_for_turns(pcm, turns, intervals):
    """turns: list of dicts with 'speaker'; intervals: list of (start, end) samples."""
    env = audio_envelope(pcm)
    cues = {}
    for turn, (start, end) in zip(turns, intervals):
        speaker = turn["speaker"]
        f0 = start // SAMPLES_PER_FRAME
        f1 = max(f0 + 1, end // SAMPLES_PER_FRAME)
        seg = env[f0:f1]
        if len(seg) == 0 or float(seg.max()) < 1e-4:   # silence (or pure tone edge)
            levels = [0] * len(seg)
        else:
            floor = float(np.percentile(seg, 10))
            peak = float(np.percentile(seg, 97))
            span = max(peak - floor, 1e-4)
            raw = [0 if v < floor + 0.22 * span else
                   2 if v > floor + 0.62 * span else 1 for v in seg]
            # min run length: merge 1-frame spikes into neighbours
            levels = _min_run(raw, MOUTH_MIN_RUN)
        runs = _runs(levels)
        cues.setdefault(speaker, []).extend(
            [f0 + r[0], f0 + r[1], r[2]] for r in runs if r[2] > 0)
    return cues


def _min_run(levels, min_len):
    out = list(levels)
    i = 0
    while i < len(out):
        j = i
        while j < len(out) and out[j] == out[i]:
            j += 1
        if j - i < min_len and 0 < j - i:
            fill = out[i - 1] if i > 0 else (out[j] if j < len(out) else 0)
            for k in range(i, j):
                out[k] = fill
        i = j
    return out


def blink_schedule(turns, intervals, total_frames, seed=42):
    """Deterministic blink frame lists per speaker (seeded RNG at compile time only)."""
    rng = random.Random(seed)
    blinks = {}
    speakers = []
    for turn, (start, end) in zip(turns, intervals):
        name = turn["speaker"]
        if name not in speakers:
            speakers.append(name)
    for name in speakers:
        frames = []
        t = rng.randint(18, 40)
        while t < total_frames - 8:
            frames.append(t)
            t += rng.randint(70, 150)
        blinks[name] = frames
    return blinks


def compile_timeline(story, pcm, intervals, seed=42):
    """Freeze the ticket + WAV alignment into integer frame events (timeline_v1).

    Everything downstream (Godot) consumes ONLY this file; the audio alignment
    from lesson.py stays the single source of timing truth.
    """
    validate_scene_plan(story)
    turns = story["turns"]
    if len(intervals) != len(turns):
        raise ValueError("Alignment intervals do not match the turn count.")
    total_frames = video_frame(len(pcm) // 2)
    speakers = []
    for turn in turns:
        if turn["speaker"] not in speakers:
            speakers.append(turn["speaker"])

    scenes, current = [], None
    events = []
    mouths = mouth_cues_for_turns(pcm, turns, intervals)
    blinks = blink_schedule(turns, intervals, total_frames, seed)
    for number, (turn, (start, end)) in enumerate(zip(turns, intervals)):
        speaker = turn["speaker"]
        start_frame = video_frame(start)
        end_frame = max(start_frame + 1, video_frame(end))
        next_frame = (video_frame(intervals[number + 1][0]) if number + 1 < len(intervals)
                      else total_frames)
        scene_id = turn.get("scene_id", "student_room")
        if scene_id != current:
            scenes.append({"scene_id": scene_id, "start_frame": start_frame})
            current = scene_id
        action = turn.get("action", "idle")
        if action not in ACTIONS:
            action = "idle"
        events.append({
            "speaker": speaker,
            "text": turn["text"],
            "start_frame": start_frame,
            "end_frame": end_frame,
            "next_frame": next_frame,
            "expression": turn.get("expression", "neutral"),
            "action": action,
            "camera": turn.get("camera", "two_shot"),
            "start_ms": round(start * 1000 / RATE),
            "end_ms": round(end * 1000 / RATE),
        })
    return {
        "schema": TIMELINE_SCHEMA,
        "renderer_version": GODOT_RENDERER_VERSION,
        "seed": seed,
        "fps": FPS,
        "width": lesson.WIDTH,
        "height": lesson.HEIGHT,
        "total_frames": total_frames,
        "title": story.get("title", ""),
        "language": story.get("language", "de-DE"),
        "level": story.get("level", "A1"),
        "scenes": scenes,
        "turns": events,
        "mouths": mouths,
        "blinks": blinks,
    }


def srt_from_timeline(timeline):
    out = []
    for number, turn in enumerate(timeline["turns"], 1):
        out.append(f"{number}\n{srt_time(turn['start_ms'])} --> {srt_time(turn['end_ms'])}"
                   f"\n{turn['text']}")
    return "\n\n".join(out) + "\n"


def _mouth_level_at(timeline, speaker, frame):
    """Timeline-level mouth level lookup (mirrors main.gd; used by tests)."""
    for run in timeline["mouths"].get(speaker, []):
        if run[0] <= frame < run[1]:
            return int(run[2])
    return 0


def write_timeline(timeline, path: Path):
    path.write_text(json.dumps(timeline, ensure_ascii=False, indent=1), encoding="utf-8")


def source_hash(story, pcm, seed):
    blob = json.dumps(story, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(blob + bytes(seed) + hashlib.sha256(pcm).digest()).hexdigest()[:24]
