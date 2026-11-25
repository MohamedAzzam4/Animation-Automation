#!/bin/bash
# Phase 3: facial expression showcase (staged).
set -e
GODOT=/home/z/my-project/work/tools/godot/Godot_v4.7.2-stable_linux.x86_64
PROJ=/home/z/my-project/work/language-video-workflow/godot3d
P3=/home/z/my-project/work/language-video-workflow/output3d/phase3
export HOME=/home/z

if [ "$1" = "1" ]; then
  FRAMES=$(python3 -c "import json; print(json.load(open('$P3/face_schedule.json'))['total_frames'] + 10)")
  DISPLAY_NUM=106
  while [ -e /tmp/.X11-unix/X$DISPLAY_NUM ]; do DISPLAY_NUM=$((DISPLAY_NUM+1)); done
  Xvfb :$DISPLAY_NUM -screen 0 1280x720x24 -nolisten tcp 2>/dev/null &
  XVFB_PID=$!
  sleep 1
  export DISPLAY=:$DISPLAY_NUM
  "$GODOT" --path "$PROJ" --rendering-driver opengl3 --write-movie "$P3/phase3.avi" \
    --fixed-fps 30 --quit-after "$FRAMES" "$PROJ/phase3.tscn" -- \
    --sched=$P3/face_schedule.json 2>&1 | grep -E "SCRIPT ERROR|GPU render|Encoding|schedule" | tail -4
  kill $XVFB_PID 2>/dev/null || true
  echo "STAGE1_DONE frames=$FRAMES"
fi
if [ "$1" = "2" ]; then
  ffmpeg -y -loglevel error -threads 2 -i "$P3/phase3.avi" -c:v libx264 -preset veryfast \
    -crf 22 -pix_fmt yuv420p -r 30 -movflags +faststart "$P3/phase_03_facial_expressions.mp4"
  rm -f "$P3/phase3.avi"
  ffmpeg -y -loglevel error -i "$P3/phase_03_facial_expressions.mp4" -vf \
    "select='eq(n\,45)+eq(n\,120)+eq(n\,210)+eq(n\,300)+eq(n\,390)+eq(n\,480)+eq(n\,570)+eq(n\,660)+eq(n\,900)+eq(n\,1080)+eq(n\,1260)+eq(n\,1380)'" \
    -vsync vfr -frames:v 12 "$P3/face_%d.png"
  python3 /home/z/my-project/scripts/contact_sheet.py "$P3" "face_*.png" "$P3/phase_03_contact_sheet.png" 4
  rm -f "$P3"/face_*.png
  ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 "$P3/phase_03_facial_expressions.mp4"
  echo "STAGE2_DONE"
fi
