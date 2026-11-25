#!/bin/bash
# Phase 6: render all four environment reels with perf stats.
set -e
GODOT=/home/z/tools/godot/Godot_v4.7.2-stable_linux.x86_64
PROJ=/home/z/my-project/work/language-video-workflow/godot3d
P6=/home/z/my-project/work/language-video-workflow/output3d/phase6
export HOME=/home/z

ENV=${1:-student_room}
while [ false ]; do
  DISPLAY_NUM=120
  while [ -e /tmp/.X11-unix/X$DISPLAY_NUM ]; do DISPLAY_NUM=$((DISPLAY_NUM+1)); done
  Xvfb :$DISPLAY_NUM -screen 0 1280x720x24 -nolisten tcp 2>/dev/null &
  XVFB=$!
  sleep 1
  export DISPLAY=:$DISPLAY_NUM
  START=$(date +%s.%N)
  FRAMES=$(python3 -c "import json; print(json.load(open('$P6/env_$ENV.json'))['total_frames'])")
  "$GODOT" --path "$PROJ" --rendering-driver opengl3 --write-movie /tmp/p6_$ENV.avi \
    --fixed-fps 30 --quit-after $((FRAMES + 5)) "$PROJ/phase5_scene.tscn" -- --sched=$P6/env_$ENV.json \
    > /tmp/p6_$ENV.log 2>&1 &
  GPID=$!
  PEAK=0
  while kill -0 $GPID 2>/dev/null; do
    RSS=$(ps -o rss= -p $GPID 2>/dev/null | tail -1)
    [ -n "$RSS" ] && [ "$RSS" -gt "$PEAK" ] && PEAK=$RSS
    sleep 1
  done
  wait $GPID || true
  END=$(date +%s.%N)
  kill $XVFB 2>/dev/null || true
  WALL=$(python3 -c "print(f'{$END - $START:.1f}')")
  FRAMES=$(grep -oE "^([0-9]+) frames" /tmp/p6_$ENV.log | head -1 | grep -oE "[0-9]+")
  echo "env=$ENV frames=$FRAMES wall=${WALL}s peak_rss_kb=$PEAK $(grep -oE 'CPU render time.*' /tmp/p6_$ENV.log | head -1)" >> $P6/perf_stats.txt
  ffmpeg -y -loglevel error -threads 2 -i /tmp/p6_$ENV.avi -c:v libx264 -preset ultrafast \
    -crf 22 -pix_fmt yuv420p -r 30 -movflags +faststart $P6/phase_06_$ENV.mp4
  echo "done $ENV"
done
cat $P6/perf_stats.txt
