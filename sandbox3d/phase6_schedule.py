#!/usr/bin/env python3
"""Phase 6: one schedule per environment — character tours + camera presets.

Cameras are YAW-RELATIVE offsets (authored in the +Z-facing frame, rotated by
the avatar's yaw each frame), so the subject stays framed in every shot.
21-28 s per env. Deterministic."""
import json
import os
import sys

FPS = 30
OUTDIR = sys.argv[1] if len(sys.argv) > 1 else "/home/z/my-project/work/language-video-workflow/output3d/phase6"
os.makedirs(OUTDIR, exist_ok=True)


def build(env, beats, camera, char_start=(0, 0, 0), turns=None, bounds=None):
    f = 0
    body, paths, expr, gaze, blinks = [], [], [], [], []
    for clip, dur, path_to, e_name, e_int in beats:
        body.append({"start_frame": f, "end_frame": f + int(dur * FPS),
                     "clip": clip, "blend": 0.4})
        if path_to:
            paths.append({"start_frame": f, "end_frame": f + int(dur * FPS),
                          "from": list(char_start), "to": list(path_to)})
        expr.append({"start_frame": f, "end_frame": f + int(dur * FPS),
                     "name": e_name, "intensity": e_int,
                     "label": e_name + "@" + clip})
        f += int(dur * FPS)
    total = f + 15
    sched = {"fps": FPS, "total_frames": total, "schema": "interaction_v1",
             "environment": env, "paths": paths, "turns": turns or [], "body": body,
             "attachments": [], "expressions": expr, "gaze": gaze,
             "blinks": blinks, "visemes": [], "head_nod": [],
             "camera": camera, "objects": {}, "door": {"pos": [9, 0, 9], "segments": []},
             "camera_bounds": bounds or []}
    return sched


def cam(start, dur, preset, pos, target, push_to=None, fov=None):
    seg = {"start_frame": int(start * FPS), "end_frame": int((start + dur) * FPS),
           "preset": preset, "pos": list(pos), "target": list(target),
           "yaw_relative": True, "smooth": True}
    if push_to:
        seg["push_to"] = list(push_to)
    if fov:
        seg["fov"] = fov
    return seg


# camera offsets in the character's facing frame (+Z front):
#   establishing: wide 3/4 front; tracking: side-follow; closeup: face;
#   medium: 3/4 front; side: full profile; fullbody: wide front.
ENVS = {
    "student_room": build("student_room", [
        ("UAL1_Idle", 4.0, None, "neutral", 0.0),
        ("UAL1_Walk", 4.0, (1.6, 0, 1.4), "neutral", 0.0),
        ("UAL1_Idle", 3.5, None, "happy", 0.5),
        ("UAL1_Idle_Talking", 5.0, None, "happy", 0.6),
        ("UAL1_Walk", 4.0, (-1.6, 0, 1.4), "neutral", 0.0),
        ("UAL1_Idle", 4.0, None, "relaxed", 0.6),
    ], [
        cam(0.0, 5.0, "establishing", (2.6, 1.7, 2.4), (0, 0.7, 0), push_to=(1.9, 1.5, 1.7), fov=50),
        cam(5.0, 4.5, "tracking", (2.0, 1.45, 0.6), (0, 0.75, 0), fov=46),
        cam(9.5, 4.0, "closeup", (0.5, 1.38, 0.8), (0, 0.95, 0), fov=30),
        cam(13.5, 4.0, "medium", (1.7, 1.3, 1.9), (0, 0.5, 0), fov=45),
        cam(17.5, 4.0, "side", (2.5, 1.3, 0.5), (0, 0.5, 0), fov=45),
        cam(21.5, 3.5, "fullbody", (1.5, 1.15, 2.6), (0, 0.55, 0), fov=44),
    ], char_start=(0.0, 0.0, 0.4), bounds=[-3.6, 3.6, -2.6, 2.6], turns=[{"start_frame": int(4.0 * FPS), "end_frame": int(4.8 * FPS), "from_yaw_deg": 0, "to_yaw_deg": 58},
              {"start_frame": int(8.0 * FPS), "end_frame": int(8.8 * FPS), "from_yaw_deg": 58, "to_yaw_deg": 0},
              {"start_frame": int(16.5 * FPS), "end_frame": int(17.3 * FPS), "from_yaw_deg": 0, "to_yaw_deg": 122},
              {"start_frame": int(20.5 * FPS), "end_frame": int(21.3 * FPS), "from_yaw_deg": 122, "to_yaw_deg": 0}]),

    "hallway": build("hallway", [
        ("UAL1_Idle", 3.0, None, "neutral", 0.0),
        ("UAL1_Walk", 5.0, (0, 0, 2.2), "neutral", 0.0),
        ("proc_turn_left", 1.0, None, "neutral", 0.0),
        ("UAL1_Walk", 5.0, (0, 0, -2.2), "neutral", 0.0),
        ("UAL1_Idle", 3.5, None, "worried", 0.5),
        ("UAL1_Idle_Talking", 4.0, None, "neutral", 0.2),
    ], [
        cam(0.0, 5.0, "establishing", (1.8, 1.8, 2.6), (0, 0.7, 0), push_to=(1.3, 1.6, 1.9), fov=50),
        cam(5.0, 5.0, "tracking", (2.0, 1.45, 0.6), (0, 0.55, 0), fov=46),
        cam(10.0, 3.5, "fullbody", (1.5, 1.05, 2.6), (0, 0.4, 0), fov=44),
        cam(13.5, 4.0, "over_shoulder", (0.9, 1.5, 1.1), (0, 0.6, -0.6), fov=42),
        cam(17.5, 4.0, "closeup", (0.5, 1.38, 0.8), (0, 0.95, 0), fov=30),
    ], char_start=(0.0, 0.0, 2.9), bounds=[-1.3, 1.3, -5.2, 5.2], turns=[{"start_frame": 0, "end_frame": int(0.8 * FPS), "from_yaw_deg": 0, "to_yaw_deg": 180}]),

    "cafe": build("cafe", [
        ("UAL1_Walk", 4.0, (-1.2, 0, 1.55), "neutral", 0.0),
        ("UAL1_Idle", 2.0, None, "neutral", 0.0),
        ("UAL1_Sitting_Enter", 2.5, (-1.2, 0, 1.42), "neutral", 0.0),
        ("UAL1_Sitting_Talking", 6.0, None, "happy", 0.65),
        ("UAL1_Sitting_Idle", 2.5, None, "relaxed", 0.5),
        ("UAL1_Sitting_Exit", 2.5, (-1.2, 0, 1.55), "neutral", 0.0),
        ("UAL1_Walk", 3.5, (1.3, 0, 1.35), "neutral", 0.0),
    ], [
        cam(0.0, 4.5, "establishing", (2.6, 1.7, 2.5), (0, 0.7, 0), push_to=(1.9, 1.5, 1.8), fov=50),
        cam(4.5, 4.0, "medium", (1.7, 1.3, 1.9), (0, 0.5, 0), fov=45),
        cam(8.5, 4.0, "over_shoulder", (0.9, 1.5, 1.1), (0, 0.6, -0.6), fov=42),
        cam(12.5, 4.0, "closeup", (0.5, 1.42, 0.8), (0, 0.42, 0), fov=30),
        cam(16.5, 4.0, "side", (2.5, 1.3, 0.5), (0, 0.5, 0), fov=45),
        cam(20.5, 3.5, "tracking", (2.0, 1.45, 0.6), (0, 0.75, 0), fov=46),
    ], char_start=(0.6, 0.0, 2.2), bounds=[-3.6, 3.6, -3.6, 3.6]),

    "park": build("park", [
        ("UAL1_Walk", 4.5, (0.4, 0, 1.2), "neutral", 0.0),
        ("UAL1_Idle", 3.5, None, "happy", 0.6),
        ("UAL1_Walk", 4.0, (0.9, 0, -0.6), "neutral", 0.0),
        ("UAL1_Idle", 3.5, None, "surprised", 0.6),
        ("UAL1_Idle_Talking", 5.0, None, "happy", 0.7),
        ("proc_wave", 3.0, None, "happy", 0.9),
        ("UAL1_Idle", 3.5, None, "neutral", 0.0),
    ], [
        cam(0.0, 5.0, "establishing", (3.0, 1.9, 2.8), (0, 0.7, 0), push_to=(2.0, 1.6, 1.9), fov=50),
        cam(5.0, 4.5, "tracking", (2.0, 1.45, 0.6), (0, 0.75, 0), fov=46),
        cam(9.5, 4.0, "fullbody", (1.5, 1.15, 2.6), (0, 0.55, 0), fov=44),
        cam(13.5, 4.0, "closeup", (0.5, 1.38, 0.8), (0, 0.95, 0), fov=30),
        cam(17.5, 4.5, "medium", (1.7, 1.3, 1.9), (0, 0.5, 0), fov=45),
        cam(22.0, 4.0, "push_in", (2.2, 1.5, 2.0), (0, 0.55, 0),
            push_to=(1.1, 1.35, 0.9), fov=42),
    ], char_start=(0.2, 0.0, 2.6), bounds=[-9.0, 9.0, -9.0, 9.0], turns=[{"start_frame": 0, "end_frame": int(0.8 * FPS), "from_yaw_deg": 0, "to_yaw_deg": 180}]),
}

for name, sched in ENVS.items():
    path = os.path.join(OUTDIR, f"env_{name}.json")
    json.dump(sched, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"{name}: {sched['total_frames']} frames ({sched['total_frames']/FPS:.1f}s) -> {path}")
