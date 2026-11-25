#!/bin/bash
# Phase 2 render, staged to fit tool timeouts:
#   stage 1: Godot Movie Maker -> AVI          (~8 min)
#   stage 2: ffmpeg encode + stills + sheet    (~1 min)
set -e
GODOT=/home/z/my-project/work/tools/godot/Godot_v4.7.2-stable_linux.x86_64
PROJ=/home/z/my-project/work/language-video-workflow/godot3d
OUT=/home/z/my-project/work/language-video-workflow/output3d/phase2
mkdir -p "$OUT"
export HOME=/home/z

if [ "$1" = "1" ]; then
  FRAMES=$(python3 -c "
durs=[4.0,4.0,2.0,2.6,2.5,3.0,2.5,3.0,2.5,2.5,2.5,4.0,1.8,3.0,2.2,1.0,1.0,2.0]
print(int(sum(durs)*30)+15)")
  DISPLAY_NUM=104
  while [ -e /tmp/.X11-unix/X$DISPLAY_NUM ]; do DISPLAY_NUM=$((DISPLAY_NUM+1)); done
  Xvfb :$DISPLAY_NUM -screen 0 1280x720x24 -nolisten tcp 2>/dev/null &
  XVFB_PID=$!
  sleep 1
  export DISPLAY=:$DISPLAY_NUM
  "$GODOT" --path "$PROJ" --rendering-driver opengl3 --write-movie "$OUT/phase2.avi" \
    --fixed-fps 30 --quit-after "$FRAMES" "$PROJ/phase2.tscn" 2>&1 | grep -E "SCRIPT ERROR|GPU render|Encoding" | tail -4
  kill $XVFB_PID 2>/dev/null || true
  echo "STAGE1_DONE frames=$FRAMES"
fi

if [ "$1" = "2" ]; then
  ffmpeg -y -loglevel error -threads 2 -i "$OUT/phase2.avi" -c:v libx264 -preset fast \
    -crf 22 -pix_fmt yuv420p -r 30 -movflags +faststart "$OUT/phase_02_body_animation.mp4"
  rm -f "$OUT/phase2.avi"
  ffmpeg -y -loglevel error -i "$OUT/phase_02_body_animation.mp4" -vf \
    "select='eq(n\,60)+eq(n\,195)+eq(n\,330)+eq(n\,480)+eq(n\,615)+eq(n\,780)+eq(n\,930)+eq(n\,1050)+eq(n\,1170)'" \
    -vsync vfr -frames:v 9 "$OUT/beat_%d.png"
  python3 /home/z/my-project/scripts/contact_sheet.py "$OUT" "beat_*.png" "$OUT/phase_02_contact_sheet.png" 3
  rm -f "$OUT"/beat_*.png
  ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 "$OUT/phase_02_body_animation.mp4"
  echo "STAGE2_DONE"
fi
