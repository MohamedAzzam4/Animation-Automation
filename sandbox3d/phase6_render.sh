#!/bin/bash
# Phase 6: four environment reels (staged per env).
set -e
GODOT=/home/z/my-project/work/tools/godot/Godot_v4.7.2-stable_linux.x86_64
PROJ=/home/z/my-project/work/language-video-workflow/godot3d
P6=/home/z/my-project/work/language-video-workflow/output3d/phase6
export HOME=/home/z
ENV=${1:-student_room}
FRAMES=$(python3 -c "import json; print(json.load(open('$P6/env_$ENV.json'))['total_frames'] + 3)")

DISPLAY_NUM=130
while [ -e /tmp/.X11-unix/X$DISPLAY_NUM ]; do DISPLAY_NUM=$((DISPLAY_NUM+1)); done
Xvfb :$DISPLAY_NUM -screen 0 1280x720x24 -nolisten tcp 2>/dev/null &
XVFB=$!
sleep 1
export DISPLAY=:$DISPLAY_NUM
"$GODOT" --path "$PROJ" --rendering-driver opengl3 --write-movie "$P6/env_$ENV.avi" \
  --fixed-fps 30 --quit-after "$FRAMES" "$PROJ/phase5_scene.tscn" -- \
  --sched=$P6/env_$ENV.json 2>&1 | grep -E "SCRIPT ERROR|GPU render" | tail -2
kill $XVFB 2>/dev/null || true
START=$(date +%s.%N)
ffmpeg -y -loglevel error -threads 2 -i "$P6/env_$ENV.avi" -c:v libx264 -preset ultrafast \
  -crf 23 -pix_fmt yuv420p -r 30 -movflags +faststart "$P6/phase_06_env_$ENV.mp4"
rm -f "$P6/env_$ENV.avi"
END=$(date +%s.%N)
echo "env_$ENV encoded in $(echo "$END - $START" | bc)s"
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 "$P6/phase_06_env_$ENV.mp4"
