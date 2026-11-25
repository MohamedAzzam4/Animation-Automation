#!/usr/bin/env python3
"""Phase 3 demo facial schedule: expression showcase at 4 intensities,
simultaneous behaviors, gaze work, nod, laugh, return-to-neutral.
Frames at 30 fps; ~52 s = 1560 frames."""
import json
import sys

FPS = 30

segs = []
blinks = []
visemes = []
gaze = []
nods = []
labels = []

t = 0


def seg(name, dur, intensity=0.0, label=None):
    global t
    segs.append({"start_frame": t, "end_frame": t + dur * FPS,
                 "name": name, "intensity": intensity, "label": label or name})
    labels.append((t, label or name))
    t += dur * FPS


def blink(delay_s):
    blinks.append({"frame": t + int(delay_s * FPS)})


# 1 neutral 1s
seg("neutral", 1.0)
# 2 happy at 4 intensities (0.25/0.5/0.75/1.0), 1.6 s each
for iv in (0.25, 0.5, 0.75, 1.0):
    seg("happy", 1.6, iv, f"happy@{iv}")
# 3 smile 1.6, sad 1.6
seg("smile", 1.6, 0.85)
seg("sad", 1.6, 0.8)
# 4 surprised 1.6
seg("surprised", 1.6, 0.9)
# 5 worried 1.8
seg("worried", 1.8, 0.7)
# 6 confused 1.6
seg("confused", 1.6, 0.55)
# 7 angry 1.8
seg("angry", 1.8, 0.85)
# 8 laugh 3 s with blinks
seg("laugh", 3.0, 1.0)
blink(0.8)
blink(2.0)
# 9 thinking 3 s with gaze up-right
seg("thinking", 3.0, 1.0)
gaze.append({"start_frame": t - int(3.0 * FPS), "end_frame": t,
             "target": [0.6, 1.9, 1.2], "label": "gaze_up_right"})
# 10 relaxed 2 s
seg("relaxed", 2.0, 0.9)
# 11 smile + blink (simultaneous) 3 s
seg("smile", 3.0, 0.8, "smile+blink")
blink(0.8)
blink(2.0)
# 12 happy + look away (gaze left) 3 s
seg("happy", 3.0, 0.7, "smile+look_left")
gaze.append({"start_frame": t - int(3.0 * FPS), "end_frame": t,
             "target": [-1.0, 1.5, 1.5], "label": "gaze_left"})
# 13 surprised + head turn to the door side 3 s
seg("surprised", 3.0, 0.85, "surprise+turn")
gaze.append({"start_frame": t - int(3.0 * FPS), "end_frame": t,
             "target": [-1.4, 1.5, 0.6], "label": "gaze_door"})
# 14 worried + nod 3 s
seg("worried", 3.0, 0.6, "concern+nod")
nods.append({"start_frame": t - int(3.0 * FPS), "end_frame": t,
             "amplitude": 0.18, "hz": 2.2})
# 15 gaze directions: left, right, up, down (neutral face), 1.5 s each
seg("neutral", 1.5, 0.0, "gaze_L")
gaze.append({"start_frame": t - int(1.5 * FPS), "end_frame": t,
             "target": [-1.2, 1.5, 1.0]})
seg("neutral", 1.5, 0.0, "gaze_R")
gaze.append({"start_frame": t - int(1.5 * FPS), "end_frame": t,
             "target": [1.2, 1.5, 1.0]})
seg("neutral", 1.5, 0.0, "gaze_UP")
gaze.append({"start_frame": t - int(1.5 * FPS), "end_frame": t,
             "target": [0.0, 2.6, 1.0]})
seg("neutral", 1.5, 0.0, "gaze_DOWN")
gaze.append({"start_frame": t - int(1.5 * FPS), "end_frame": t,
             "target": [0.0, 0.2, 1.0]})
# 16 gaze to camera 2.5 s
seg("neutral", 2.5, 0.0, "gaze_camera")
gaze.append({"start_frame": t - int(2.5 * FPS), "end_frame": t,
             "target": ["camera"]})
# 17 blinks alone 2 s
seg("neutral", 2.0, 0.0, "blinks_only")
blink(0.5)
blink(1.4)
# 18 return to neutral (from worried) 2 s
seg("worried", 1.0, 0.5, "returning")
seg("neutral", 1.0, 0.0, "neutral_end")

out = {
    "fps": FPS,
    "total_frames": t,
    "expressions": segs,
    "blinks": blinks,
    "visemes": visemes,
    "gaze": gaze,
    "head_nod": nods,
}
path = sys.argv[1] if len(sys.argv) > 1 else "/home/z/my-project/work/language-video-workflow/output3d/phase3/face_schedule.json"
json.dump(out, open(path, "w"), indent=1)
labels_path = path.replace(".json", "_labels.json")
json.dump({"fps": FPS, "labels": [{"frame": f, "text": s} for f, s in labels]},
          open(labels_path, "w"), indent=1)
print(f"schedule: {t} frames ({t/FPS:.1f}s), {len(segs)} segments, "
      f"{len(blinks)} blinks, {len(gaze)} gaze, {len(nods)} nods -> {path}")
