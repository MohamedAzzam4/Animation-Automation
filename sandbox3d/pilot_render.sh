#!/bin/bash
# Render one pilot scene: args = scene number
set -e
GODOT=/home/z/my-project/work/tools/godot/Godot_v4.7.2-stable_linux.x86_64
PROJ=/home/z/my-project/work/language-video-workflow/godot3d
P=/home/z/my-project/work/language-video-workflow/output3d/pilot
SCENE=$1
export HOME=/home/z
SDIR=$P/scene$SCENE
FRAMES=$(python3 -c "import json; print(json.load(open('$SDIR/compiled_timeline.json'))['total_frames'] + 3)")

DISPLAY_NUM=130
while [ -e /tmp/.X11-unix/X$DISPLAY_NUM ]; do DISPLAY_NUM=$((DISPLAY_NUM+1)); done
Xvfb :$DISPLAY_NUM -screen 0 1280x720x24 -nolisten tcp 2>/dev/null &
XVFB=$!
sleep 1
export DISPLAY=:$DISPLAY_NUM

"$GODOT" --path "$PROJ" --rendering-driver opengl3 --write-movie $SDIR/scene.avi \
  --fixed-fps 30 --quit-after "$FRAMES" "$PROJ/phase5_scene.tscn" -- \
  --sched=$SDIR/compiled_timeline.json > $SDIR/render.log 2>&1
kill $XVFB 2>/dev/null || true

ffmpeg -y -loglevel error -threads 2 -i $SDIR/scene.avi -i $SDIR/audio.wav \
  -map 0:v -map 1:a -c:v libx264 -preset ultrafast -crf 21 -pix_fmt yuv420p -r 30 \
  -c:a aac -b:a 128k -shortest $SDIR/scene.mp4
rm -f $SDIR/scene.avi
echo "scene $SCENE done: $FRAMES frames"
ffprobe -v error -show_entries format=duration -of csv=p=0 $SDIR/scene.mp4
