#!/bin/bash
# Phase 5: interaction reel (staged).
set -e
GODOT=/home/z/my-project/work/tools/godot/Godot_v4.7.2-stable_linux.x86_64
PROJ=/home/z/my-project/work/language-video-workflow/godot3d
P5=/home/z/my-project/work/language-video-workflow/output3d/phase5
export HOME=/home/z

if [ "$1" = "1" ]; then
  FRAMES=$(python3 -c "import json; print(json.load(open('$P5/interaction_schedule.json'))['total_frames'] + 5)")
  DISPLAY_NUM=116
  while [ -e /tmp/.X11-unix/X$DISPLAY_NUM ]; do DISPLAY_NUM=$((DISPLAY_NUM+1)); done
  Xvfb :$DISPLAY_NUM -screen 0 1280x720x24 -nolisten tcp 2>/dev/null &
  XVFB=$!
  sleep 1
  export DISPLAY=:$DISPLAY_NUM
  "$GODOT" --path "$PROJ" --rendering-driver opengl3 --write-movie "$P5/phase5.avi" \
    --fixed-fps 30 --quit-after "$FRAMES" "$PROJ/phase5_scene.tscn" -- \
    --sched=$P5/interaction_schedule.json 2>&1 | grep -E "SCRIPT ERROR|GPU render|director loaded" | tail -3
  kill $XVFB 2>/dev/null || true
  echo "STAGE1_DONE"
fi
if [ "$1" = "2" ]; then
  ffmpeg -y -loglevel error -threads 2 -i "$P5/phase5.avi" -c:v libx264 -preset ultrafast \
    -crf 24 -pix_fmt yuv420p -r 30 -movflags +faststart "$P5/phase_05_interaction.mp4"
  rm -f "$P5/phase5.avi"
  ffmpeg -y -loglevel error -i "$P5/phase_05_interaction.mp4" -vf \
    "select=eq(n\,15)+eq(n\,80)+eq(n\,290)+eq(n\,415)+eq(n\,490)+eq(n\,650)+eq(n\,690)+eq(n\,990)'" \
    -vsync vfr -frames:v 8 "$P5/beat_%d.png"
  python3 /home/z/my-project/scripts/contact_sheet.py "$P5" "beat_*.png" "$P5/phase_05_contact_sheet.png" 4
  rm -f "$P5"/beat_*.png
  ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 "$P5/phase_05_interaction.mp4"
  echo "STAGE2_DONE"
fi
