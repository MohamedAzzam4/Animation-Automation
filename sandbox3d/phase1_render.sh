#!/bin/bash
# Phase 1: character inspection reel (6 views, 15 s).
set -e
GODOT=/home/z/my-project/work/tools/godot/Godot_v4.7.2-stable_linux.x86_64
PROJ=/home/z/my-project/work/language-video-workflow/godot3d
OUT=/home/z/my-project/work/language-video-workflow/output3d/phase1
mkdir -p "$OUT"
export HOME=/home/z

DISPLAY_NUM=100
while [ -e /tmp/.X11-unix/X$DISPLAY_NUM ]; do DISPLAY_NUM=$((DISPLAY_NUM+1)); done
Xvfb :$DISPLAY_NUM -screen 0 1280x720x24 -nolisten tcp 2>/dev/null &
XVFB_PID=$!
sleep 1
export DISPLAY=:$DISPLAY_NUM

"$GODOT" --path "$PROJ" --rendering-driver opengl3 --write-movie "$OUT/phase1.avi" \
  --fixed-fps 30 --quit-after 450 "$PROJ/phase1.tscn" 2>&1 | grep -E "ERROR|SCRIPT|GPU render|Encoding" | tail -6
kill $XVFB_PID 2>/dev/null || true

ffmpeg -y -loglevel error -threads 2 -i "$OUT/phase1.avi" -c:v libx264 -preset fast \
  -crf 22 -pix_fmt yuv420p -r 30 -movflags +faststart "$OUT/phase_01_character_inspection.mp4"
rm -f "$OUT/phase1.avi"

# contact sheet: one frame per view (middle of each 75-frame slot)
ffmpeg -y -loglevel error -i "$OUT/phase_01_character_inspection.mp4" -vf \
  "select='eq(n\,37)+eq(n\,112)+eq(n\,187)+eq(n\,262)+eq(n\,337)+eq(n\,412)',scale=424:238" \
  -vsync vfr -frames:v 6 "$OUT/view_%d.png"
python3 /home/z/my-project/scripts/contact_sheet.py "$OUT" "view_*.png" "$OUT/phase_01_contact_sheet.png" 3
ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height -show_entries format=duration -of default=noprint_wrappers=1 "$OUT/phase_01_character_inspection.mp4"
