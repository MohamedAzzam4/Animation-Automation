#!/usr/bin/env python3
"""Phase 7: JSON-driven story compiler (3d_story_v1 -> interaction schedule).

Pipeline: story JSON -> validation against the capability catalog -> per-line
espeak-ng German audio (free local TTS, disclosed; word-exact timing) -> parallel
absolute-frame tracks (body/paths/turns/facial/visemes/blinks/camera/objects/
subtitles/fades) -> schedule JSON consumed by godot3d/director.gd + SRT + WAV.

Semantic actions are compiled to verified low-level capability IDs; unknown IDs are
rejected with a clear error BEFORE rendering (never silently replaced).
"""
import json
import os
import subprocess
import sys
import unicodedata
import wave

import numpy as np

RATE = 22050
FPS = 30
GAP_SENT_MS = 260

# ---------------- capability catalog (verified in phases 1-6) ----------------
CATALOG = {
    "schema": "capability_catalog_v1",
    "actions": {
        "idle": {"clip": "UAL1_Idle", "min_dur": 2.5},
        "walk_to": {"clip": "UAL1_Walk", "min_dur": 3.0, "needs": "target_anchor"},
        "sit": {"clip": "UAL1_Sitting_Enter", "min_dur": 3.0, "needs": "chair_anchor"},
        "sit_idle": {"clip": "UAL1_Sitting_Idle", "min_dur": 2.5, "needs": "chair_anchor"},
        "stand": {"clip": "UAL1_Sitting_Exit", "min_dur": 3.0, "needs": "chair_anchor"},
        "talk_gesture": {"clip": "UAL1_Idle_Talking", "min_dur": 3.5},
        "sit_talk_gesture": {"clip": "UAL1_Sitting_Talking", "min_dur": 4.0, "needs": "chair_anchor"},
        "wave": {"clip": "proc_wave", "min_dur": 4.0},
        "point_at": {"clip": "proc_point_right", "min_dur": 1.8},
        "think": {"clip": "proc_think", "min_dur": 2.5},
        "nod": {"clip": "UAL2_Yes", "min_dur": 2.0},
        "shake_head": {"clip": "UAL2_Idle_No", "min_dur": 2.0},
        "fold_arms": {"clip": "UAL2_Idle_FoldArms", "min_dur": 2.5},
        "read_book": {"clip": "proc_hold_book", "min_dur": 4.5, "needs": "book"},
        "drink": {"clip": "proc_think", "min_dur": 4.5, "needs": "mug"},
        "look_around": {"clip": "UAL1_Idle", "min_dur": 1.5},
    },
    "expressions": {
        "neutral": 0.0, "happy": 1.0, "smile": 1.0, "sad": 1.0, "surprised": 1.0,
        "angry": 1.0, "laugh": 1.0, "relaxed": 1.0,
        "worried": 0.7, "confused": 0.5, "thinking": 0.8,   # documented approximations
    },
    "gaze_targets": ["camera", "door", "mug", "book", "window", "table", "forward", "trees", "bench", "chair"],
    "cameras": ["establishing", "medium", "closeup", "fullbody", "side",
                "over_shoulder", "tracking", "push_in"],
    "environments": {
        "student_room": {
            "walk_start": [0.0, 0.0, 0.4],
            "anchors": {"chair": [-0.75, 0.0, 0.22], "chair_approach": [-0.75, 0.0, 0.58],
                        "mug": [-0.85, 0.74, 0.86], "book": [-0.55, 0.74, 0.88],
                        "door": [1.6, 1.3, 0.6], "table": [-0.75, 0.95, 1.05],
                        "forward": [0.0, 1.5, 2.5], "window": [-2.9, 1.4, 0.6]},
            "start_yaw": -60,
        },
        "hallway": {
            "walk_start": [0.0, 0.0, 2.9],
            "anchors": {"door": [0.0, 1.3, -3.4], "forward": [0.0, 1.5, -2.0],
                        "camera": [0, 0, 0]},
            "start_yaw": 180,
        },
        "cafe": {
            "walk_start": [0.6, 0.0, 2.2],
            "anchors": {"chair": [-1.2, 0.0, 1.42], "chair_approach": [-1.2, 0.0, 1.55],
                        "mug": [-1.34, 0.79, 0.5], "book": [-1.06, 0.79, 0.5],
                        "table": [-1.2, 0.95, 0.6], "door": [2.9, 1.3, -1.0],
                        "forward": [0.0, 1.5, 2.0], "window": [0.5, 1.45, -2.4]},
            "start_yaw": -90,
        },
        "park": {
            "walk_start": [0.2, 0.0, 2.6],
            "anchors": {"door": [9.0, 1.3, 9.0], "forward": [0.0, 1.5, -2.0],
                        "bench": [0.9, 1.0, 1.4], "trees": [-3.2, 1.4, -2.0]},
            "start_yaw": 180,
        },
    },
    "priority_rules": {
        "body": "one clip at a time; later beats replace earlier (0.4s blend)",
        "expression": "one composite at a time, latest wins, 0.3s crossfade",
        "visemes": "mouth-only shapes; additive with expressions; latest wins",
        "blink": "additive over anything (EYE_Close, clamped)",
        "gaze": "latest segment wins; head follows large yaw",
        "locomotion": "walk clips suppress baked root yaw; position/yaw owned by paths/turns",
    },
}


def S(sec):
    return int(sec * FPS)


def espeak_word(text: str, out_wav: str, speed: int = 120) -> float:
    subprocess.run(["espeak-ng", "-v", "de", "-s", str(speed), "-a", "180",
                    "-w", out_wav, text], check=True, capture_output=True)
    with wave.open(out_wav, "rb") as w:
        return w.getnframes() / w.getframerate()


def espeak_ipa(text: str, speed: int = 120) -> str:
    r = subprocess.run(["espeak-ng", "-v", "de", "-s", str(speed), "-q", "--ipa", text],
                       capture_output=True, text=True, check=True)
    return r.stdout.strip()


DUR_TABLE = {
    "a": 80, "aː": 130, "eː": 125, "ɛ": 80, "ɛː": 120, "ə": 55,
    "iː": 125, "ɪ": 80, "i": 80, "oː": 125, "ɔ": 80, "o": 80,
    "uː": 125, "ʊ": 80, "u": 80, "øː": 120, "œ": 80, "yː": 120, "ʏ": 80, "y": 80,
    "aɪ": 170, "aʊ": 170, "ɔʏ": 170,
    "m": 70, "n": 70, "ŋ": 70, "l": 65, "ʀ": 65, "ʁ": 65, "r": 60, "ɐ": 60,
    "f": 80, "v": 70, "s": 80, "z": 75, "ʃ": 85, "ʒ": 80, "ç": 75, "x": 75, "h": 55,
    "p": 55, "b": 55, "t": 50, "d": 55, "k": 55, "ɡ": 60, "g": 60, "tʃ": 90, "j": 55,
    "ʔ": 30,
}
VISEME = {
    "a": ("A", 1.0), "aː": ("A", 1.0), "ɑ": ("A", 1.0), "ɑː": ("A", 1.0),
    "eː": ("E", 0.75), "ɛ": ("E", 0.75), "ɛː": ("E", 0.8), "ə": ("E", 0.45),
    "iː": ("I", 0.75), "ɪ": ("I", 0.7), "i": ("I", 0.75),
    "oː": ("O", 0.9), "ɔ": ("O", 0.85), "o": ("O", 0.9),
    "uː": ("U", 0.9), "ʊ": ("U", 0.85), "u": ("U", 0.9),
    "øː": ("O", 0.5), "œ": ("O", 0.45), "yː": ("U", 0.5), "ʏ": ("U", 0.45), "y": ("U", 0.5),
    "f": ("U", 0.3), "v": ("U", 0.3),
    "s": ("E", 0.45), "z": ("E", 0.4), "ʃ": ("E", 0.5), "ʒ": ("E", 0.5),
    "ç": ("E", 0.3), "x": ("E", 0.35), "h": ("E", 0.25),
    "n": ("E", 0.2), "ŋ": ("E", 0.2), "l": ("E", 0.25), "ʀ": ("E", 0.25),
    "ʁ": ("E", 0.25), "r": ("E", 0.2), "ɐ": ("E", 0.3),
    "t": ("E", 0.15), "d": ("E", 0.15), "k": ("E", 0.15), "ɡ": ("E", 0.2), "g": ("E", 0.2),
    "j": ("I", 0.4), "p": (None, 0.0), "b": (None, 0.0), "m": (None, 0.0), "ʔ": (None, 0.0),
}


def phonemes_to_visemes(ipa: str, start_ms: float, dur_ms: float):
    ipa = unicodedata.normalize("NFC", ipa).replace("ˈ", "").replace("ˌ", "").replace("‿", "")
    ipa = ipa.replace("t͡ʃ", "tʃ").replace("p͡f", "pf").replace("a͡ɪ", "aɪ") \
        .replace("a͡ʊ", "aʊ").replace("ɔ͡ʏ", "ɔʏ")
    ph_list, i = [], 0
    two = ["aɪ", "aʊ", "ɔʏ", "tʃ", "pf", "aɛ"]
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
    merged = []
    for p in ph_list:
        if p == "ː" and merged:
            merged[-1] = merged[-1] + "ː"
        else:
            merged.append(p)
    merged = ["ɡ" if p == "ɡ" else p for p in merged]
    weights = [DUR_TABLE.get(p, 60) for p in merged]
    if not weights:
        return []
    scale = dur_ms / sum(weights)
    pos = start_ms
    out = []
    for p, w in zip(merged, weights):
        shape_w = VISEME.get(p)
        if shape_w and shape_w[0]:
            out.append({"shape": shape_w[0].lower(), "weight": shape_w[1],
                        "start_frame": int(pos * FPS / 1000),
                        "end_frame": max(int(pos * FPS / 1000) + 1,
                                         int((pos + w * scale) * FPS / 1000)),
                        "phoneme": p})
        pos += w * scale
    # merge same-shape neighbours
    m = []
    for v in out:
        if m and m[-1]["shape"] == v["shape"] and v["start_frame"] - m[-1]["end_frame"] <= 1:
            m[-1]["end_frame"] = v["end_frame"]
        else:
            m.append(dict(v))
    return m


def srt_time(ms):
    h, rem = divmod(ms, 3600000)
    m, rem = divmod(rem, 60000)
    s, ms2 = divmod(rem, 1000)
    return f"{h:02d}:{m:02d}:{s:02d},{ms2:03d}"


def validate(story):
    if story.get("schema_version") != "3d_story_v1":
        raise ValueError(f"schema_version must be '3d_story_v1', got {story.get('schema_version')!r}")
    errors = []
    for si, scene in enumerate(story.get("scenes", []), 1):
        env = scene.get("environment")
        if env not in CATALOG["environments"]:
            errors.append(f"scene {si}: unknown environment '{env}'. "
                          f"Allowed: {', '.join(CATALOG['environments'])}")
        for ti, turn in enumerate(scene.get("turns", []), 1):
            action = turn.get("action", "idle")
            if action not in CATALOG["actions"]:
                errors.append(f"scene {si} turn {ti}: unknown action '{action}'. "
                              f"Allowed: {', '.join(CATALOG['actions'])}")
            ex = turn.get("expression", {})
            if isinstance(ex, dict):
                name = ex.get("name", "neutral")
                if name not in CATALOG["expressions"]:
                    errors.append(f"scene {si} turn {ti}: unknown expression '{name}'. "
                                  f"Allowed: {', '.join(CATALOG['expressions'])}")
                iv = ex.get("intensity", 1.0)
                if not (0.0 <= float(iv) <= 1.0):
                    errors.append(f"scene {si} turn {ti}: intensity {iv} outside 0..1")
            elif ex not in (None, "neutral"):
                errors.append(f"scene {si} turn {ti}: expression must be an object")
            g = turn.get("gaze_target")
            if g is not None and g not in CATALOG["gaze_targets"]:
                errors.append(f"scene {si} turn {ti}: unknown gaze_target '{g}'. "
                              f"Allowed: {', '.join(CATALOG['gaze_targets'])}")
            cam = turn.get("camera", "medium")
            if cam not in CATALOG["cameras"]:
                errors.append(f"scene {si} turn {ti}: unknown camera '{cam}'. "
                              f"Allowed: {', '.join(CATALOG['cameras'])}")
            if "text" not in turn:
                errors.append(f"scene {si} turn {ti}: missing 'text' (every turn speaks)")
            if env in CATALOG["environments"]:
                needs = CATALOG["actions"].get(action, {}).get("needs")
                anchor_map = {"target_anchor": None, "chair_anchor": "chair",
                              "mug": "mug", "book": "book"}
                anchor = anchor_map.get(needs)
                if anchor and anchor not in CATALOG["environments"][env]["anchors"]:
                    errors.append(f"scene {si} turn {ti}: action '{action}' needs anchor "
                                  f"'{anchor}' which environment '{env}' does not provide")
    if errors:
        raise ValueError("Story validation failed:\n  - " + "\n  - ".join(errors))
    return True


# camera preset -> concrete pose per environment (computed from env bounds)
CAM_POSES = {
    "student_room": {
        "establishing": {"pos": [2.35, 2.05, 1.9], "target": [0, 0.9, 0], "fov": 55},
        "medium": {"pos": [0.7, 1.3, 2.1], "target": [-0.5, 1.0, 0.4], "fov": 45},
        "closeup": {"pos": [-0.15, 1.5, 1.15], "target": [-0.7, 1.42, 0.35], "fov": 30},
        "fullbody": {"pos": [0.6, 1.1, 2.9], "target": [-0.7, 0.85, 0.3], "fov": 44},
        "side": {"pos": [0.8, 1.3, 1.0], "target": [-0.75, 1.0, 0.3], "fov": 45},
        "over_shoulder": {"pos": [-0.15, 1.5, 1.0], "target": [-0.8, 1.1, 0.0], "fov": 42},
        "tracking": {"pos": [0.8, 1.5, -1.2], "target": [0, 1.05, 0.4], "fov": 46},
        "push_in": {"pos": [1.6, 1.5, 1.9], "target": [-0.5, 1.1, 0.2], "fov": 42},
    },
    "hallway": {
        "establishing": {"pos": [0.0, 1.85, 3.3], "target": [0, 1.0, 0], "fov": 52},
        "medium": {"pos": [0.7, 1.3, 1.2], "target": [0, 1.0, -0.5], "fov": 45},
        "closeup": {"pos": [0.25, 1.5, 1.15], "target": [0, 1.42, 0.3], "fov": 30},
        "fullbody": {"pos": [1.0, 1.1, 2.4], "target": [0, 0.85, 0.0], "fov": 44},
        "side": {"pos": [1.3, 1.3, 0.6], "target": [0, 1.0, 0.4], "fov": 45},
        "over_shoulder": {"pos": [0.3, 1.5, 1.0], "target": [0, 1.2, -0.6], "fov": 42},
        "tracking": {"pos": [0.7, 1.5, -1.4], "target": [0, 1.1, 0.6], "fov": 46},
        "push_in": {"pos": [0.5, 1.6, 2.4], "target": [0, 1.1, 0.0], "fov": 42},
    },
    "cafe": {
        "establishing": {"pos": [2.5, 2.0, 2.1], "target": [-0.5, 0.9, 0.4], "fov": 55},
        "medium": {"pos": [0.4, 1.3, 2.7], "target": [-1.2, 1.0, 0.9], "fov": 45},
        "closeup": {"pos": [-0.62, 1.5, 1.9], "target": [-1.25, 1.42, 1.2], "fov": 30},
        "fullbody": {"pos": [0.6, 1.1, 2.9], "target": [-1.2, 0.85, 1.0], "fov": 44},
        "side": {"pos": [-2.6, 1.35, 1.4], "target": [-1.2, 1.0, 1.4], "fov": 45},
        "over_shoulder": {"pos": [-0.55, 1.5, 2.35], "target": [-1.2, 1.05, 0.6], "fov": 42},
        "tracking": {"pos": [1.0, 1.5, -1.0], "target": [1.3, 1.1, 0.7], "fov": 46},
        "push_in": {"pos": [1.2, 1.6, 2.6], "target": [-1.0, 1.1, 1.0], "fov": 42},
    },
    "park": {
        "establishing": {"pos": [5.5, 3.0, 5.5], "target": [0, 1.0, 0], "fov": 50},
        "medium": {"pos": [2.4, 1.3, 1.8], "target": [0.3, 1.05, -0.3], "fov": 45},
        "closeup": {"pos": [0.7, 1.5, 0.6], "target": [0.1, 1.42, -0.1], "fov": 30},
        "fullbody": {"pos": [2.6, 1.0, 2.8], "target": [0.6, 0.9, -0.4], "fov": 44},
        "side": {"pos": [2.9, 1.3, 0.4], "target": [0.4, 1.0, 0.0], "fov": 45},
        "over_shoulder": {"pos": [0.85, 1.5, 1.3], "target": [0.2, 1.15, -0.4], "fov": 42},
        "tracking": {"pos": [0.8, 1.6, -1.5], "target": [0, 1.1, 0.4], "fov": 46},
        "push_in": {"pos": [2.2, 1.5, 1.9], "target": [0.3, 1.2, -0.3], "fov": 42},
    },
}



import math


def _cam_relative(cam_name, char_pos, yaw_deg, env, walk_dest=None):
    """Character-relative camera pose. front = facing dir, right = 90 deg right."""
    yaw = math.radians(yaw_deg)
    front = Vector2 = (math.sin(yaw), math.cos(yaw))          # (x, z)
    right = (math.cos(yaw), -math.sin(yaw))
    cx, cy, cz = char_pos[0], char_pos[1], char_pos[2]
    if cam_name == "establishing":
        room = {"student_room": (2.35, 2.05, 1.9), "hallway": (0.0, 1.85, 3.3),
                "cafe": (2.5, 2.0, 2.1), "park": (5.5, 3.0, 5.5)}
        tgt = {"student_room": (0, 0.9, 0), "hallway": (0, 1.0, 0),
               "cafe": (-0.5, 0.9, 0.4), "park": (0, 1.0, 0)}
        return {"pos": list(room[env]), "target": list(tgt[env]), "fov": 55}
    if cam_name == "medium":
        pos = [cx + front[0] * 2.2 + right[0] * 0.5, cy + 1.3, cz + front[1] * 2.2 + right[1] * 0.5]
        return {"pos": pos, "target": [cx, cy + 1.05, cz], "fov": 45}
    if cam_name == "closeup":
        pos = [cx + front[0] * 0.95 + right[0] * 0.32, cy + 1.52, cz + front[1] * 0.95 + right[1] * 0.32]
        return {"pos": pos, "target": [cx, cy + 1.44, cz], "fov": 30}
    if cam_name == "fullbody":
        pos = [cx + front[0] * 3.4 + right[0] * 0.7, cy + 1.0, cz + front[1] * 3.4 + right[1] * 0.7]
        return {"pos": pos, "target": [cx, cy + 0.85, cz], "fov": 44}
    if cam_name == "side":
        pos = [cx + right[0] * 2.6, cy + 1.3, cz + right[1] * 2.6]
        return {"pos": pos, "target": [cx, cy + 1.0, cz], "fov": 45}
    if cam_name == "over_shoulder":
        pos = [cx + front[0] * 1.0 + right[0] * 0.55, cy + 1.55, cz + front[1] * 1.0 + right[1] * 0.55]
        return {"pos": pos, "target": [cx + front[0] * 2.4, cy + 1.1, cz + front[1] * 2.4], "fov": 42}
    if cam_name == "tracking":
        if walk_dest:
            dx, dz = walk_dest[0] - cx, walk_dest[2] - cz
            ln = max(0.001, (dx * dx + dz * dz) ** 0.5)
            back = (-dx / ln, -dz / ln)
        else:
            back = (-front[0], -front[1])
        pos = [cx + back[0] * 1.7 + right[0] * 0.5, cy + 1.55, cz + back[1] * 1.7 + right[1] * 0.5]
        return {"pos": pos, "target": [cx, cy + 1.1, cz], "fov": 46}
    if cam_name == "push_in":
        pos = [cx + front[0] * 2.8 + right[0] * 0.6, cy + 1.6, cz + front[1] * 2.8 + right[1] * 0.6]
        push = [cx + front[0] * 1.2 + right[0] * 0.3, cy + 1.4, cz + front[1] * 1.2 + right[1] * 0.3]
        return {"pos": pos, "target": [cx, cy + 1.1, cz], "fov": 42, "push_to": push}
    return {"pos": [cx + front[0] * 2.2, cy + 1.3, cz + front[1] * 2.2],
            "target": [cx, cy + 1.05, cz], "fov": 45}


def compile_story(story, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    validate(story)
    seed = int(story.get("seed", 42))
    import random
    rng = random.Random(seed)

    body, paths, turns, expr = [], [], [], []
    gaze, blinks, visemes, nods = [], [], [], []
    attachments, subtitles, fades = [], [], []
    scenes_track = []
    door_segments, objects = [], {}
    audio_chunks = []       # (start_ms, samples)
    chunks_info = []
    f = 0
    prev_env = None
    prev_cam_end_pose = None
    cur_yaw = 0.0
    srt_entries = []
    walk_speed = 2.0        # m/s approx for path duration

    for si, scene in enumerate(story["scenes"]):
        scene_start = f
        env = scene["environment"]
        envd = CATALOG["environments"][env]
        anchors = envd["anchors"]
        for name, pos in anchors.items():
            if name in ("mug", "book") and env not in objects:
                pass
        first_turn = scene["turns"][0]
        # ---- scene entry: fade + establishing if camera set at scene level ----
        if prev_env is not None:
            fades.append({"start_frame": f - 6, "end_frame": f + 24,
                          "mode": "out_in"})
        # place avatar at env start
        start = envd["walk_start"]
        if prev_env is None:
            paths.append({"start_frame": 0, "end_frame": 0,
                          "from": list(start), "to": list(start)})
        else:
            # teleport-free: the fade hides the scene change; position resets in the dark
            paths.append({"start_frame": f + 12, "end_frame": f + 13,
                          "from": list(start), "to": list(start)})
        turns.append({"start_frame": f, "end_frame": f + 1,
                      "from_yaw_deg": envd["start_yaw"], "to_yaw_deg": envd["start_yaw"]})
        cur_yaw = float(envd["start_yaw"])
        prev_env = env

        for ti, turn in enumerate(scene["turns"], 1):
            action = turn.get("action", "idle")
            ex = turn.get("expression", {}) or {}
            ex_name = ex.get("name", "neutral") if isinstance(ex, dict) else str(ex)
            ex_int = float(ex.get("intensity", 1.0)) if isinstance(ex, dict) else 1.0
            gaze_t = turn.get("gaze_target", "forward")
            cam_name = turn.get("camera", "medium")
            pause_ms = int(turn.get("pause_ms", 400))
            text = turn["text"]

            # ---- audio for this turn ----
            line_wav = os.path.join(out_dir, f"line_s{si}_t{ti}.wav")
            speech_dur = espeak_word(text, line_wav)
            ipa = espeak_ipa(text)
            speech_ms = int(speech_dur * 1000)
            chunk_start_ms = int(f / FPS * 1000) + 500  # lead-in after beat start
            with wave.open(line_wav, "rb") as w:
                samples = np.frombuffer(w.readframes(w.getnframes()), dtype=np.int16)
            audio_chunks.append((chunk_start_ms, samples))
            chunks_info.append({"turn": f"s{si}t{ti}", "start_ms": chunk_start_ms,
                                "dur_ms": speech_ms})

            # ---- visual beat duration ----
            act = CATALOG["actions"][action]
            beat_dur_ms = max(act["min_dur"] * 1000, 500 + speech_ms + pause_ms)
            beat_dur = beat_dur_ms / 1000.0
            speech_frames = int((500 + speech_ms) * FPS / 1000)

            # ---- body layer ----
            clip = act["clip"]
            if action == "walk_to":
                target_name = turn.get("target_anchor", "chair_approach" if "chair_approach" in anchors else "door")
                dest = anchors.get(target_name, anchors["forward"])
                dest[1] = 0.0
                dist = ((dest[0] - start[0]) ** 2 + (dest[2] - start[2]) ** 2) ** 0.5
                walk_dur = max(beat_dur, dist / walk_speed + 0.8)
                body.append({"start_frame": f, "end_frame": f + S(walk_dur),
                             "clip": clip, "blend": 0.4})
                import math
                path_yaw = math.degrees(math.atan2(dest[0] - start[0], dest[2] - start[2]))
                turns.append({"start_frame": f, "end_frame": f + S(0.4),
                              "from_yaw_deg": cur_yaw, "to_yaw_deg": path_yaw})
                cur_yaw = path_yaw
                paths.append({"start_frame": f, "end_frame": f + S(walk_dur),
                              "from": list(start), "to": list(dest)})
                start = dest
                beat_frames = S(walk_dur)
            elif action == "sit":
                body.append({"start_frame": f, "end_frame": f + S(2.5),
                             "clip": clip, "blend": 0.4})
                ca = anchors["chair_approach"]
                cs = anchors["chair"]
                paths.append({"start_frame": f, "end_frame": f + S(2.5),
                              "from": list(ca), "to": list(cs)})
                start = cs
                beat_frames = S(2.5)
                # pad the remaining beat with sit_idle
                rest_ms = beat_dur_ms - 2500
                if rest_ms > 200:
                    body.append({"start_frame": f + S(2.5), "end_frame": f + S(2.5 + rest_ms / 1000.0),
                                 "clip": "UAL1_Sitting_Idle", "blend": 0.3})
            elif action == "stand":
                body.append({"start_frame": f, "end_frame": f + S(2.5),
                             "clip": clip, "blend": 0.4})
                ca = anchors.get("chair_approach", anchors["forward"])
                paths.append({"start_frame": f, "end_frame": f + S(2.5),
                              "from": list(start), "to": list(ca)})
                start = list(ca)
                beat_frames = S(2.5)
                rest_ms = beat_dur_ms - 2500
                if rest_ms > 200:
                    body.append({"start_frame": f + S(2.5), "end_frame": f + S(2.5 + rest_ms / 1000.0),
                                 "clip": "UAL1_Idle", "blend": 0.3})
            elif action == "drink":
                # look + reach + grab + sip pose + return
                mug = anchors["mug"]
                drink_frames = S(beat_dur)
                body.append({"start_frame": f, "end_frame": f + S(1.8),
                             "clip": "proc_point_right", "blend": 0.4})
                attachments.append({"frame": f + S(1.2), "object": "mug", "mode": "hand",
                                    "bone": "RightHand", "offset": [0.0, -0.07, 0.02],
                                    "tween_frames": 8})
                body.append({"start_frame": f + S(1.8), "end_frame": f + S(1.8 + beat_dur / 1000.0 - 1.8 - 1.0),
                             "clip": "proc_think", "blend": 0.4})
                attachments.append({"frame": f + drink_frames - S(1.0), "object": "mug",
                                    "mode": "world", "pos": list(mug), "tween_frames": 22})
                body.append({"start_frame": f + drink_frames - S(1.0),
                             "end_frame": f + drink_frames,
                             "clip": "UAL1_Sitting_Idle" if start == anchors.get("chair") else "UAL1_Idle",
                             "blend": 0.5})
                beat_frames = drink_frames
            elif action == "read_book":
                book = anchors["book"]
                read_frames = S(beat_dur)
                body.append({"start_frame": f, "end_frame": f + S(1.6),
                             "clip": "proc_hold_book", "blend": 0.4})
                attachments.append({"frame": f + S(1.0), "object": "book", "mode": "hand",
                                    "bone": "LeftHand", "offset": [0.0, 0.02, 0.10],
                                    "tween_frames": 8})
                body.append({"start_frame": f + S(1.6), "end_frame": f + read_frames - S(0.8),
                             "clip": "proc_hold_book", "blend": 0.0})
                attachments.append({"frame": f + read_frames - S(0.8), "object": "book",
                                    "mode": "world", "pos": list(book), "tween_frames": 22})
                body.append({"start_frame": f + read_frames - S(0.8),
                             "end_frame": f + read_frames,
                             "clip": "UAL1_Sitting_Idle" if start == anchors.get("chair") else "UAL1_Idle",
                             "blend": 0.5})
                beat_frames = read_frames
            else:
                body.append({"start_frame": f, "end_frame": f + S(beat_dur),
                             "clip": clip, "blend": 0.4})
                beat_frames = S(beat_dur)
                if action == "wave":
                    pass

            # ---- facial layer (covers the whole beat) ----
            expr.append({"start_frame": f, "end_frame": f + beat_frames,
                         "name": ex_name, "intensity": ex_int,
                         "label": f"s{si}t{ti}:{ex_name}@{ex_int}"})
            if action in ("drink", "read_book"):
                # neutral during the reach portion would fight the expression; keep it

                pass
            # visemes over the speech window
            for v in phonemes_to_visemes(ipa, chunk_start_ms, speech_ms):
                v["word"] = text[:18]
                visemes.append(v)
            # gaze
            if gaze_t == "camera":
                gaze.append({"start_frame": f, "end_frame": f + beat_frames,
                             "target": ["camera"]})
            else:
                pos = anchors.get(gaze_t, anchors["forward"])
                gaze.append({"start_frame": f, "end_frame": f + beat_frames,
                             "target": [pos[0], pos[1], pos[2]]})
            # seeded blinks: every 2.4-4.2 s within the beat
            t_ms = 500
            while t_ms < beat_dur_ms - 400:
                blinks.append({"frame": f + int(t_ms * FPS / 1000)})
                t_ms += rng.randint(2400, 4200)
            if ex_name == "worried" and rng.random() < 0.8:
                nods.append({"start_frame": f + S(0.5), "end_frame": f + S(min(2.0, beat_dur)),
                             "amplitude": 0.14, "hz": 2.0})

            # ---- camera layer (character-relative) ----
            pose = _cam_relative(cam_name, start, cur_yaw, env,
                                 dest if action == "walk_to" else None)
            seg = {"start_frame": f, "end_frame": f + beat_frames,
                   "preset": cam_name, "pos": list(pose["pos"]),
                   "target": list(pose["target"]), "fov": pose["fov"],
                   "smooth": prev_cam_end_pose is not None and ti > 1}
            if cam_name == "push_in":
                seg["push_to"] = list(pose["push_to"])
            camera_segs_list = CAMERA_SEGS
            camera_segs_list.append(seg)
            prev_cam_end_pose = pose

            # ---- subtitles ----
            start_ms = int(f / FPS * 1000) + 500
            subtitles.append({"start_frame": f + S(0.3), "end_frame": f + speech_frames,
                              "text": text, "turn": f"s{si}t{ti}"})
            srt_entries.append((start_ms, start_ms + speech_ms, text))

            # ---- door logic: when walking to the door in hallway ----
            if env == "hallway" and turn.get("gaze_target") == "door" and ti >= 1 and \
                    not door_done.get(env, False):
                door_segments.append({"start_frame": f + S(0.8),
                                      "end_frame": f + S(0.8 + 1.6), "to_deg": 75})
                door_done[env] = True

            advance = beat_frames
            f += advance
        scenes_track.append({"environment": env, "start_frame": scene_start,
                             "end_frame": f})

    # merge consecutive same-camera segments
    merged_cam = []
    for seg in CAMERA_SEGS:
        if merged_cam and merged_cam[-1]["preset"] == seg["preset"] and \
                merged_cam[-1]["pos"] == seg["pos"] and \
                seg["start_frame"] - merged_cam[-1]["end_frame"] <= 1:
            merged_cam[-1]["end_frame"] = seg["end_frame"]
        else:
            merged_cam.append(dict(seg))

    total = f + S(0.5)
    # ---- build audio track ----
    total_ms = int(total / FPS * 1000)
    track = np.zeros(int(total_ms / 1000 * RATE) + RATE)
    for start_ms, samples in audio_chunks:
        i0 = int(start_ms / 1000 * RATE)
        i1 = min(len(track), i0 + len(samples))
        track[i0:i1] += samples[:i1 - i0]
    peak = np.abs(track).max()
    if peak > 0.99:
        track *= 0.99 / peak
    wav_path = os.path.join(out_dir, "audio.wav")
    with wave.open(wav_path, "wb") as w:
        w.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        w.writeframesraw((np.clip(track, -1, 1) * 32767).astype("<i2").tobytes())

    # ---- SRT ----
    srt = []
    for n, (a, b, text) in enumerate(srt_entries, 1):
        srt.append(f"{n}\n{srt_time(a)} --> {srt_time(b)}\n{text}")
    with open(os.path.join(out_dir, "subtitles.srt"), "w", encoding="utf-8") as fh:
        fh.write("\n\n".join(srt) + "\n")

    scene_objects = {}
    f_cursor = 0
    for scene in story["scenes"]:
        env = scene["environment"]
        anchors = CATALOG["environments"][env]["anchors"]
        objs = {}
        for obj in ("mug", "book"):
            if obj in anchors:
                objs[obj] = {"pos": list(anchors[obj])}
        scene_objects[env] = objs
    sched = {
        "schema": "interaction_v1",
        "fps": FPS, "total_frames": total,
        "environment": story["scenes"][0]["environment"],
        "paths": paths, "turns": turns, "body": body,
        "attachments": attachments,
        "expressions": expr, "gaze": gaze, "blinks": blinks,
        "visemes": visemes, "head_nod": nods,
        "camera": merged_cam,
        "scenes": scenes_track,
        "scene_objects": scene_objects,
        "subtitles": subtitles, "fades": fades,
        "door": {"pos": CATALOG["environments"][story["scenes"][0]["environment"]]
                 ["anchors"].get("door", [9, 0, 9]),
                 "segments": door_segments},
        "objects": objects, "audio_file": wav_path,
    }
    json.dump(sched, open(os.path.join(out_dir, "compiled_timeline.json"), "w"),
              indent=1, ensure_ascii=False)
    json.dump({"seed": seed, "turns": chunks_info,
               "audio": wav_path, "text": story["title"],
               "source": "espeak-ng de (free local TTS), per-line synthesis; "
                         "phoneme visemes via espeak IPA + duration table (approximation)"},
              open(os.path.join(out_dir, "audio_manifest.json"), "w"),
              indent=1, ensure_ascii=False)
    print(f"compiled: {total} frames ({total/FPS:.1f}s), {len(body)} body segs, "
          f"{len(expr)} expressions, {len(visemes)} visemes, {len(merged_cam)} camera segs")
    return sched


# module-level camera accumulator + door dedup
CAMERA_SEGS = []
door_done = {}


def reset_compiler():
    global CAMERA_SEGS, door_done
    CAMERA_SEGS = []
    door_done = {}


if __name__ == "__main__":
    story = json.load(open(sys.argv[1], encoding="utf-8"))
    out_dir = sys.argv[2] if len(sys.argv) > 2 else "/home/z/my-project/work/language-video-workflow/output3d/pilot"
    reset_compiler()
    compile_story(story, out_dir)


def compile_story_split(story, out_dir):
    """Render-friendly mode: one schedule + audio per scene (fades at both edges).
    Concatenate the rendered clips with ffmpeg concat afterwards."""
    os.makedirs(out_dir, exist_ok=True)
    total_manifest = []
    for si, scene in enumerate(story["scenes"], 1):
        sub = dict(story)
        sub["scenes"] = [scene]
        sub["title"] = f"{story['title']} - scene {si}"
        sub["seed"] = int(story.get("seed", 42)) + si
        reset_compiler()
        sched = compile_story(sub, os.path.join(out_dir, f"scene{si}"))
        total_manifest.append({"scene": si, "environment": scene["environment"],
                               "frames": sched["total_frames"],
                               "dir": os.path.join(out_dir, f"scene{si}")})
    json.dump(total_manifest, open(os.path.join(out_dir, "render_manifest.json"), "w"),
              indent=1)
    print("split scenes:", [(m["scene"], m["frames"]) for m in total_manifest])
    return total_manifest
