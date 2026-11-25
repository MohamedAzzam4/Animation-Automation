#!/usr/bin/env python3
"""Phase 6: one schedule per environment — character tours + camera presets +
ambient effects. 21 s each (630 frames). Deterministic."""
import json
import sys

FPS = 30
OUTDIR = sys.argv[1] if len(sys.argv) > 1 else "/home/z/my-project/work/language-video-workflow/output3d/phase6"
import os
os.makedirs(OUTDIR, exist_ok=True)


def build(env, beats, camera, char_start=(0, 0, 0)):
    """beats: [(clip, dur, path_to, face_expr, face_intensity)]"""
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
             "environment": env, "paths": paths, "turns": [], "body": body,
             "attachments": [], "expressions": expr, "gaze": gaze,
             "blinks": blinks, "visemes": [], "head_nod": [],
             "camera": camera, "objects": {}, "door": {"pos": [9, 0, 9], "segments": []}}
    return sched


def cam(start, dur, preset, pos, target, push_to=None, fov=None, smooth=False):
    seg = {"start_frame": int(start * FPS), "end_frame": int((start + dur) * FPS),
           "preset": preset, "pos": list(pos), "target": list(target),
           "smooth": smooth}
    if push_to:
        seg["push_to"] = list(push_to)
    if fov:
        seg["fov"] = fov
    return seg


ENVS = {
    # ---- student room: apartment-ish layout, character at (0,0,0.4) ----
    "student_room": build("student_room", [
        ("UAL1_Idle", 4.0, None, "neutral", 0.0),
        ("UAL1_Walk", 4.0, (1.6, 0, 1.4), "neutral", 0.0),
        ("UAL1_Idle", 3.5, None, "happy", 0.5),
        ("UAL1_Idle_Talking", 5.0, None, "happy", 0.6),
        ("UAL1_Walk", 4.0, (-1.6, 0, 1.4), "neutral", 0.0),
        ("UAL1_Idle", 4.0, None, "relaxed", 0.6),
    ], [
        cam(0.0, 5.0, "establishing", (2.35, 2.05, 1.9), (0, 0.9, 0),
            push_to=(1.9, 1.8, 1.5), fov=55, smooth=False),
        cam(5.0, 4.5, "tracking", (0.9, 1.5, -1.3), (0, 1.05, 0.35), fov=48, smooth=True),
        cam(9.5, 4.0, "closeup", (0.85, 1.45, 1.05), (0.15, 1.42, 0.75), fov=30, smooth=True),
        cam(13.5, 4.0, "medium", (1.9, 1.25, 2.5), (-0.4, 1.0, 0.6), fov=45, smooth=True),
        cam(17.5, 4.0, "side", (2.9, 1.3, 1.0), (-1.2, 1.0, 1.0), fov=45, smooth=True),
    ], char_start=(0.0, 0.0, 0.4)),

    # ---- hallway: long room; walk the runner, lamps breathe ----
    "hallway": build("hallway", [
        ("UAL1_Idle", 3.0, None, "neutral", 0.0),
        ("UAL1_Walk", 5.0, (0, 0, 2.2), "neutral", 0.0),
        ("proc_turn_left", 1.0, None, "neutral", 0.0),
        ("UAL1_Walk", 5.0, (0, 0, -2.2), "neutral", 0.0),
        ("UAL1_Idle", 3.5, None, "worried", 0.5),
        ("UAL1_Idle_Talking", 4.0, None, "neutral", 0.2),
    ], [
        cam(0.0, 5.0, "establishing", (0.0, 1.85, 3.3), (0, 1.0, 0),
            push_to=(0.0, 1.6, 2.6), fov=52, smooth=False),
        cam(5.0, 5.0, "tracking", (0.7, 1.5, -1.4), (0, 1.1, 0.6), fov=46, smooth=True),
        cam(10.0, 3.5, "fullbody", (1.6, 1.1, 3.6), (0, 0.85, -1.6), fov=44, smooth=True),
        cam(13.5, 4.0, "over_shoulder", (0.75, 1.5, -1.15), (0, 1.15, -2.6), fov=42, smooth=True),
        cam(17.5, 4.0, "closeup", (0.55, 1.42, -2.75), (0, 1.4, -2.1), fov=30, smooth=True),
    ], char_start=(0.0, 0.0, 2.9)),

    # ---- cafe: tables with steam, pendant lamps ----
    "cafe": build("cafe", [
        ("UAL1_Walk", 4.0, (-1.2, 0, 1.55), "neutral", 0.0),
        ("UAL1_Idle", 2.0, None, "neutral", 0.0),
        ("UAL1_Sitting_Enter", 2.5, (-1.2, 0, 1.42), "neutral", 0.0),
        ("UAL1_Sitting_Talking", 6.0, None, "happy", 0.65),
        ("UAL1_Sitting_Idle", 2.5, None, "relaxed", 0.5),
        ("UAL1_Sitting_Exit", 2.5, (-1.2, 0, 1.55), "neutral", 0.0),
        ("UAL1_Walk", 3.5, (1.3, 0, 1.35), "neutral", 0.0),
    ], [
        cam(0.0, 4.5, "establishing", (2.5, 2.0, 2.1), (-0.5, 0.9, 0.4),
            push_to=(2.0, 1.75, 1.7), fov=55, smooth=False),
        cam(4.5, 4.0, "medium", (0.4, 1.3, 2.7), (-1.2, 1.0, 0.9), fov=45, smooth=True),
        cam(8.5, 4.0, "over_shoulder", (-0.55, 1.5, 2.35), (-1.2, 1.05, 0.6), fov=42, smooth=True),
        cam(12.5, 4.0, "closeup", (-0.6, 1.5, 1.85), (-1.25, 1.42, 1.15), fov=30, smooth=True),
        cam(16.5, 4.0, "side", (-2.6, 1.35, 1.3), (-1.2, 1.0, 1.4), fov=45, smooth=True),
        cam(20.5, 3.5, "tracking", (1.0, 1.5, -1.0), (1.3, 1.1, 0.7), fov=46, smooth=True),
    ], char_start=(0.6, 0.0, 2.2)),

    # ---- park: trees, clouds, leaves, sun ----
    "park": build("park", [
        ("UAL1_Walk", 4.5, (0.4, 0, 1.2), "neutral", 0.0),
        ("UAL1_Idle", 3.5, None, "happy", 0.6),
        ("UAL1_Walk", 4.0, (0.9, 0, -0.6), "neutral", 0.0),
        ("UAL1_Idle", 3.5, None, "surprised", 0.6),
        ("UAL1_Idle_Talking", 5.0, None, "happy", 0.7),
        ("proc_wave", 3.0, None, "happy", 0.9),
        ("UAL1_Idle", 3.5, None, "neutral", 0.0),
    ], [
        cam(0.0, 5.0, "establishing", (5.5, 3.0, 5.5), (0, 1.0, 0),
            push_to=(4.0, 2.2, 4.0), fov=50, smooth=False),
        cam(5.0, 4.5, "tracking", (0.8, 1.6, -1.5), (0, 1.1, 0.4), fov=46, smooth=True),
        cam(9.5, 4.0, "fullbody", (2.6, 1.0, 2.8), (0.6, 0.9, -0.4), fov=44, smooth=True),
        cam(13.5, 4.0, "closeup", (0.7, 1.5, 0.35), (0.1, 1.45, -0.3), fov=30, smooth=True),
        cam(17.5, 4.5, "medium", (2.4, 1.3, 1.8), (0.3, 1.05, -0.3), fov=45, smooth=True),
        cam(22.0, 4.0, "push_in", (2.2, 1.5, 1.6), (0.2, 1.2, -0.5),
            push_to=(1.0, 1.35, 0.2), fov=42, smooth=True),
    ], char_start=(0.2, 0.0, 2.6)),
}

for name, sched in ENVS.items():
    path = os.path.join(OUTDIR, f"env_{name}.json")
    json.dump(sched, open(path, "w"), indent=1, ensure_ascii=False)
    print(f"{name}: {sched['total_frames']} frames ({sched['total_frames']/FPS:.1f}s) -> {path}")
