#!/usr/bin/env python3
"""Phase 5: interaction schedule — PARALLEL track compilation.

Tracks (all absolute-frame, all simultaneous):
  body    : clip segments (one active at a time)
  paths   : avatar position (walk drives it)
  turns   : avatar yaw
  expressions/gaze/blinks/visemes/head_nod : facial layers (FaceDriver)
  attachments/door : explicit-frame object events

The compiler walks scene BEATS: each beat has a body clip + duration and emits
facial segments covering the SAME frames. No stacking.
"""
import json
import sys

FPS = 30
OUT = sys.argv[1] if len(sys.argv) > 1 else "/home/z/my-project/work/language-video-workflow/output3d/phase5/interaction_schedule.json"

CHAIR_APPROACH = (-0.75, 0.0, 0.58)
CHAIR_SIT = (-0.75, 0.0, 0.22)
TABLE_TOP = 0.74
MUG_HOME = (-0.85, TABLE_TOP, 0.86)
BOOK_HOME = (-0.55, TABLE_TOP, 0.88)
DOOR_POS = (1.60, 0.0, 0.60)

body, paths, turns = [], [], []
expr, gaze, blinks, visemes, nods = [], [], [], [], []
attachments = []
door = []

f = 0  # scene clock (frames)


def S(sec):
    return int(sec * FPS)


def beat_body(clip, dur, blend=0.4):
    body.append({"start_frame": f, "end_frame": f + S(dur), "clip": clip, "blend": blend})


def beat_path(frm, to, start=None, dur=None):
    paths.append({"start_frame": f if start is None else start,
                  "end_frame": f + S(dur) if dur else (start or 0) + S(dur or 0),
                  "from": list(frm), "to": list(to)})


def face(name, dur, intensity=0.0, label=None, offset=0.0):
    expr.append({"start_frame": f + S(offset), "end_frame": f + S(offset + dur),
                 "name": name, "intensity": intensity, "label": label or name})


def look(target, dur, label="", offset=0.0):
    gaze.append({"start_frame": f + S(offset), "end_frame": f + S(offset + dur),
                 "target": list(target) if not (len(target) == 1 and target[0] == "camera") else ["camera"],
                 "label": label})


def blink(offset):
    blinks.append({"frame": f + S(offset)})


def nod(dur, offset=0.0, amp=0.15, hz=2.0):
    nods.append({"start_frame": f + S(offset), "end_frame": f + S(offset + dur),
                 "amplitude": amp, "hz": hz})


def advance(dur):
    global f
    f += S(dur)


# ---- beat 1: idle, look around the room (1.0s) ----
beat_body("UAL1_Idle", 1.0, 0.0)
turns.append({"start_frame": 0, "end_frame": S(1.0), "from_yaw_deg": 0, "to_yaw_deg": -60})
face("neutral", 1.0)
look([DOOR_POS[0], 1.3, DOOR_POS[2]], 1.0, "look_to_room")
advance(1.0)

# ---- beat 2: walk to the chair via a clear via-point (2.6s) ----
beat_body("UAL1_Walk", 2.6, 0.5)
paths.append({"start_frame": f, "end_frame": f + S(1.6),
              "from": [0.0, 0.0, 0.0], "to": [-0.25, 0.0, 0.62]})
paths.append({"start_frame": f + S(1.6), "end_frame": f + S(2.6),
              "from": [-0.25, 0.0, 0.62], "to": list(CHAIR_APPROACH)})
face("neutral", 2.6)
look([CHAIR_APPROACH[0], 1.2, CHAIR_APPROACH[2] + 1.5], 2.6, "walk_gaze")
blink(1.2)
advance(2.6)

# ---- beat 3: turn to face the table (1.0s) ----
beat_body("proc_turn_right", 1.0, 0.4)
turns.append({"start_frame": f, "end_frame": f + S(1.0), "from_yaw_deg": -60, "to_yaw_deg": 0})
face("neutral", 1.0)
look([MUG_HOME[0], 0.85, MUG_HOME[2]], 1.0, "look_table")
advance(1.0)

# ---- beat 4: sit down with a glide onto the seat (2.5s) ----
beat_body("UAL1_Sitting_Enter", 2.5, 0.4)
paths.append({"start_frame": f, "end_frame": f + S(2.5),
              "from": list(CHAIR_APPROACH), "to": list(CHAIR_SIT)})
face("neutral", 2.5)
look([MUG_HOME[0], 0.85, MUG_HOME[2]], 2.5, "pre_sit_gaze")
advance(2.5)

# ---- beat 5: seated small talk — speech (fixture visemes) + happy + nods (5.0s) ----
talk_start = f
beat_body("UAL1_Sitting_Talking", 5.0, 0.5)
face("happy", 5.0, 0.6)
look([0.6, 1.5, 1.6], 2.5, "talk_gaze_camera_side")
look([0.0, 1.5, 2.5], 2.5, "talk_gaze_forward", offset=2.5)
blink(2.0)
blink(4.1)
nod(2.0, offset=1.0)
ph4 = json.load(open("/home/z/my-project/work/language-video-workflow/output3d/phase4/viseme_schedule.json"))
for v in ph4["visemes"]:
    if v["end_frame"] <= 150:  # first 5 s of the fixture
        visemes.append({"shape": v["shape"], "weight": v["weight"],
                        "start_frame": talk_start + v["start_frame"],
                        "end_frame": talk_start + v["end_frame"]})
advance(5.0)

# ---- beat 6: look at the mug and reach (1.0 + 1.8s) ----
beat_body("UAL1_Sitting_Idle", 1.0, 0.3)
face("neutral", 1.0)
look([MUG_HOME[0], MUG_HOME[1] + 0.05, MUG_HOME[2]], 1.0, "look_mug")
advance(1.0)

reach_start = f
beat_body("proc_point_right", 1.8, 0.4)
face("neutral", 1.8)
look([MUG_HOME[0], MUG_HOME[1] + 0.05, MUG_HOME[2]], 1.8, "reach_gaze")
attachments.append({"frame": reach_start + S(1.0), "object": "mug", "mode": "hand",
                    "bone": "RightHand", "offset": [0.0, -0.07, 0.02], "tween_frames": 8})
advance(1.8)

# ---- beat 7: drink — the hand-to-mouth pose carries the attached mug (3.0s) ----
beat_body("proc_think", 3.0, 0.4)
face("happy", 3.0, 0.7, "drinking")
look([0.0, 1.5, 2.0], 3.0, "drink_gaze")
advance(3.0)

# ---- beat 8: put the mug back (detach + deterministic tween) (1.2s) ----
attachments.append({"frame": f, "object": "mug", "mode": "world",
                    "pos": list(MUG_HOME), "tween_frames": 22})
beat_body("UAL1_Sitting_Idle", 1.2, 0.5)
face("neutral", 1.2)
look([MUG_HOME[0], MUG_HOME[1] + 0.05, MUG_HOME[2]], 1.2, "watch_mug")
advance(1.2)

# ---- beat 9: look at the book, pick it up with the left hand (0.8 + 2.2s) ----
beat_body("UAL1_Sitting_Idle", 0.8, 0.3)
face("neutral", 0.8)
look([BOOK_HOME[0], BOOK_HOME[1] + 0.03, BOOK_HOME[2]], 0.8, "look_book")
advance(0.8)

reach2_start = f
beat_body("proc_hold_book", 2.2, 0.4)
face("neutral", 2.2)
look([BOOK_HOME[0], BOOK_HOME[1] + 0.03, BOOK_HOME[2]], 2.2, "book_reach_gaze")
attachments.append({"frame": reach2_start + S(0.9), "object": "book", "mode": "hand",
                    "bone": "LeftHand", "offset": [0.0, 0.02, 0.10], "tween_frames": 8})
advance(2.2)

# ---- beat 10: examine the book (thinking face + read gaze) (2.6s) ----
beat_body("proc_hold_book", 2.6, 0.0)
face("thinking", 2.6, 0.8, "examining")
look([BOOK_HOME[0] - 0.1, 1.0, BOOK_HOME[2]], 2.6, "read_gaze")
blink(1.9)
advance(2.6)

# ---- beat 11: book back, brief idle (0.6s) ----
attachments.append({"frame": f, "object": "book", "mode": "world",
                    "pos": list(BOOK_HOME), "tween_frames": 22})
beat_body("UAL1_Sitting_Idle", 0.6, 0.3)
face("neutral", 0.6)
look([0.0, 1.5, 2.0], 0.6, "up_from_book")
advance(0.6)

# ---- beat 12: stand up (glide off the seat) (2.5s) ----
exit_start = f
beat_body("UAL1_Sitting_Exit", 2.5, 0.4)
paths.append({"start_frame": exit_start, "end_frame": exit_start + S(2.5),
              "from": list(CHAIR_SIT), "to": list(CHAIR_APPROACH)})
face("neutral", 2.5)
look([DOOR_POS[0], 1.3, DOOR_POS[2]], 2.5, "prestand_door_gaze")
advance(2.5)

# door starts opening while she stands up
door = [{"start_frame": exit_start + S(1.0), "end_frame": exit_start + S(2.6), "to_deg": 75}]

# ---- beat 13: walk to the door, surprised (3.0s) ----
walk2_start = f
beat_body("UAL1_Walk", 3.0, 0.5)
paths.append({"start_frame": walk2_start, "end_frame": walk2_start + S(3.0),
              "from": list(CHAIR_APPROACH), "to": [1.05, 0.0, 0.45]})
face("surprised", 3.0, 0.75, "surprise_at_door")
look([DOOR_POS[0], 1.3, DOOR_POS[2]], 3.0, "walk_to_door_gaze")
blink(1.5)
advance(3.0)

# ---- beat 14: wave at the visitor (3.0s) ----
beat_body("proc_wave", 3.0, 0.5)
face("happy", 3.0, 0.9, "greeting")
look([DOOR_POS[0], 1.35, DOOR_POS[2]], 3.0, "wave_gaze")
advance(3.0)

# ---- beat 15: settle to neutral, look into the camera (1.5s) ----
beat_body("UAL1_Idle", 1.5, 0.5)
face("neutral", 1.5, 0.0, "neutral_end")
look(["camera"], 1.5, "final_camera_gaze")
advance(1.5)

total = f + S(0.5)
sched = {
    "fps": FPS, "total_frames": total,
    "schema": "interaction_v1",
    "environment": "test_room",
    "objects": {"mug": {"pos": list(MUG_HOME)}, "book": {"pos": list(BOOK_HOME)}},
    "chair_anchor": list(CHAIR_SIT),
    "door": {"pos": list(DOOR_POS), "segments": door},
    "paths": paths, "turns": turns, "body": body,
    "attachments": attachments,
    "expressions": expr, "gaze": gaze, "blinks": blinks,
    "visemes": visemes, "head_nod": nods,
}
json.dump(sched, open(OUT, "w"), indent=1, ensure_ascii=False)
print(f"interaction schedule: {total} frames ({total/FPS:.1f}s), {len(body)} body beats, "
      f"{len(paths)} paths, {len(attachments)} attach events, {len(expr)} expression segments")
