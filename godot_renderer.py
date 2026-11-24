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
import os
import random
import subprocess
import time
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
    version = story.get("schema_version")
    if version is not None and version != SCHEMA:
        raise ValueError(f"Unsupported ticket schema_version '{version}'. "
                         f"This renderer supports '{SCHEMA}'.")
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


# --------------------------------------------------------------------------- #
# Phase 6: offline video export (Godot Movie Maker from Python + FFmpeg mux)


def find_godot():
    """Locate the Godot 4 binary: GODOT_BIN env, PATH, common install spots."""
    import shutil
    candidates = []
    env = os.environ.get("GODOT_BIN")
    if env:
        candidates.append(env)
    which = shutil.which("godot") or shutil.which("godot4")
    if which:
        candidates.append(which)
    candidates += [
        "/usr/local/bin/godot", "/opt/godot/Godot_v4.7.2-stable_linux.x86_64",
    ]
    for c in candidates:
        try:
            out = subprocess.run([c, "--version"], capture_output=True, text=True,
                                 timeout=30, check=True).stdout.strip()
        except (OSError, subprocess.SubprocessError):
            continue
        if out.startswith("4."):
            return c, out
    raise RuntimeError("Godot 4 binary not found. Set GODOT_BIN or install Godot 4 "
                       "from https://godotengine.org/download/ .")


class _Xvfb:
    """Owns a private Xvfb display for the render (the sandbox reaps background
    processes between commands, so each render brings its own display)."""

    def __init__(self):
        self.proc = None
        self.display = None
        self._external = None

    def __enter__(self):
        self._external = os.environ.get("DISPLAY")
        if self._external:
            return self._external
        display = 90
        while Path(f"/tmp/.X11-unix/X{display}").exists():
            display += 1
        self.display = f":{display}"
        self.proc = subprocess.Popen(
            ["Xvfb", self.display, "-screen", "0", "1280x720x24", "-nolisten", "tcp"],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(50):
            if Path(f"/tmp/.X11-unix/X{self.display[1:]}").exists():
                return self.display
            time.sleep(0.1)
        raise RuntimeError("Could not start Xvfb for the Godot render.")

    def __exit__(self, *exc):
        if self.proc:
            self.proc.terminate()
            try:
                self.proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.proc.kill()


def render_godot(story, output, key=None, model=lesson.TTS_MODEL, demo=False, *, routes=None):
    """Compile + render a lesson through Godot Movie Maker and mux with FFmpeg.

    The audio path is IDENTICAL to the pillow renderer (one whole-lesson TTS request,
    cached WAV, local Whisper alignment; demo tones offline). Deterministic: same
    ticket + WAV + seed -> same timeline and same schedule of frames.
    """
    import tempfile
    import wave as wave_mod

    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    validate_scene_plan(story)
    turns = story["turns"]
    (output / "script.json").write_text(
        json.dumps(story, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    # ---- audio (reused from lesson.py verbatim) ----
    if demo:
        pcm, intervals = lesson.demo_track(turns)
    else:
        try:
            import stable_whisper
        except ImportError as exc:
            raise RuntimeError('Install local alignment first: python -m pip install '
                               '"stable-ts==2.19.1"') from exc
        recording, pcm = lesson.speech_track(story, output, key, model, routes=routes)
        intervals = lesson.align_speech(stable_whisper, recording, story, len(pcm) // 2)
        pcm, intervals = lesson.add_pauses(pcm, intervals, turns)

    # ---- cache: identical source -> reuse ----
    digest = source_hash(story, pcm, 42)
    assets_digest = _assets_hash()
    manifest_path = output / "render_manifest.json"
    wanted = ["video.mp4", "audio.wav", "subtitles.srt", "godot_timeline.json",
              "render_manifest.json"]
    if manifest_path.is_file() and all((output / n).is_file() for n in wanted):
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        if (manifest.get("source_hash") == digest
                and manifest.get("renderer_version") == GODOT_RENDERER_VERSION
                and manifest.get("assets_hash") == assets_digest):
            print("Reusing cached Godot render (source hash unchanged).")
            return output / "video.mp4"

    timeline = compile_timeline(story, pcm, intervals, seed=42)
    total_frames = timeline["total_frames"]
    write_timeline(timeline, output / "godot_timeline.json")

    # pad audio to the exact frame count and write the WAV
    samples = total_frames * SAMPLES_PER_FRAME
    padded = pcm + bytes(2 * (samples - len(pcm) // 2))
    with wave_mod.open(str(output / "audio.wav"), "wb") as track:
        track.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        track.writeframesraw(padded)
    (output / "subtitles.srt").write_text(srt_from_timeline(timeline), encoding="utf-8")

    godot_bin, godot_version = find_godot()
    godot_project = Path(__file__).resolve().parent / "godot"

    # import pass keeps the GDScript/texture cache fresh (stale caches broke
    # earlier runs; this is cheap and deterministic)
    subprocess.run([godot_bin, "--headless", "--path", str(godot_project), "--import"],
                   check=True, capture_output=True, timeout=300)

    with tempfile.TemporaryDirectory(prefix="godot-render-") as tmp:
        avi = Path(tmp) / "video.avi"
        env = dict(os.environ, HOME=str(Path.home()))
        with _Xvfb() as display:
            env["DISPLAY"] = display
            subprocess.run(
                [godot_bin, "--path", str(godot_project), "--rendering-driver", "opengl3",
                 "--write-movie", str(avi), "--fixed-fps", "30",
                 "--quit-after", str(total_frames + 10),
                 "--", "--timeline", str((output / "godot_timeline.json").resolve())],
                check=True, capture_output=True, timeout=30 + total_frames, env=env)
        # mux: Godot video + original (padded) audio; exact duration
        subprocess.run(
            ["ffmpeg", "-y", "-hide_banner", "-loglevel", "error", "-nostdin",
             "-i", str(avi), "-i", str(output / "audio.wav"),
             "-map", "0:v", "-map", "1:a",
             "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
             "-r", "30", "-c:a", "aac", "-b:a", "128k",
             "-t", f"{total_frames / FPS:.9f}",
             "-movflags", "+faststart", str(output / "video.mp4")],
            check=True, timeout=600)

    manifest = {
        "renderer": "godot", "renderer_version": GODOT_RENDERER_VERSION,
        "godot_version": godot_version, "seed": 42,
        "source_hash": digest, "assets_hash": assets_digest,
        "total_frames": total_frames, "fps": FPS, "schema": SCHEMA,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    return output / "video.mp4"


def _assets_hash():
    base = Path(__file__).resolve().parent / "godot" / "assets"
    h = hashlib.sha256()
    for f in sorted(base.rglob("*")):
        if f.is_file() and f.name != "assets_manifest.json":
            h.update(f.name.encode())
            h.update(f.read_bytes())
    return h.hexdigest()[:16]
