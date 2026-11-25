#!/bin/bash
# Phase 0: minimal 3D scene -> Movie Maker AVI -> FFmpeg MP4 (no audio yet)
set -e
GODOT=/home/z/my-project/work/tools/godot/Godot_v4.7.2-stable_linux.x86_64
PROJ=/home/z/my-project/work/language-video-workflow/godot3d
OUT=/home/z/my-project/work/phase0
FRAMES=${1:-150}
mkdir -p "$OUT"

export HOME=/home/z
DISPLAY_NUM=90
while [ -e /tmp/.X11-unix/X$DISPLAY_NUM ]; do DISPLAY_NUM=$((DISPLAY_NUM+1)); done
Xvfb :$DISPLAY_NUM -screen 0 1280x720x24 -nolisten tcp &
XVFB_PID=$!
sleep 1
export DISPLAY=:$DISPLAY_NUM

"$GODOT" --path "$PROJ" --rendering-driver opengl3 \
  --write-movie "$OUT/phase0.avi" --fixed-fps 30 \
  --quit-after "$FRAMES" "$PROJ/phase0.tscn" 2>&1 | tail -5

kill $XVFB_PID 2>/dev/null || true

ffmpeg -y -hide_banner -loglevel error -nostdin -i "$OUT/phase0.avi" \
  -c:v libx264 -preset fast -crf 20 -pix_fmt yuv420p -r 30 \
  -movflags +faststart "$OUT/phase_00_environment.mp4"

ffprobe -v error -select_streams v:0 -show_entries stream=codec_name,width,height,nb_frames,duration -of default=noprint_wrappers=1 "$OUT/phase_00_environment.mp4"
