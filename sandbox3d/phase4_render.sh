#!/bin/bash
# Phase 4: lip-sync reels (staged):
#   1 = render Method A (amplitude) AVI
#   2 = render Method B (viseme) AVI
#   3 = encode both + side-by-side + audio mux
set -e
GODOT=/home/z/my-project/work/tools/godot/Godot_v4.7.2-stable_linux.x86_64
PROJ=/home/z/my-project/work/language-video-workflow/godot3d
P4=/home/z/my-project/work/language-video-workflow/output3d/phase4
export HOME=/home/z

start_xvfb() {
  DISPLAY_NUM=112
  while [ -e /tmp/.X11-unix/X$DISPLAY_NUM ]; do DISPLAY_NUM=$((DISPLAY_NUM+1)); done
  Xvfb :$DISPLAY_NUM -screen 0 1280x720x24 -nolisten tcp 2>/dev/null &
  XVFB=$!
  sleep 1
  export DISPLAY=:$DISPLAY_NUM
}

if [ "$1" = "1" ]; then
  start_xvfb
  "$GODOT" --path "$PROJ" --rendering-driver opengl3 --write-movie /tmp/p4a.avi \
    --fixed-fps 30 --quit-after 925 "$PROJ/phase4_lipsync.tscn" -- \
    --sched=$P4/amplitude_schedule.json --log=$P4/amplitude_driver_log.csv \
    --label=Method_A_amplitude 2>&1 | grep -E "SCRIPT ERROR|GPU render" | tail -2
  kill $XVFB 2>/dev/null || true
  echo "A_DONE"
fi
if [ "$1" = "2" ]; then
  start_xvfb
  "$GODOT" --path "$PROJ" --rendering-driver opengl3 --write-movie /tmp/p4b.avi \
    --fixed-fps 30 --quit-after 925 "$PROJ/phase4_lipsync.tscn" -- \
    --sched=$P4/viseme_schedule.json --log=$P4/viseme_driver_log.csv \
    --label=Method_B_phoneme_viseme 2>&1 | grep -E "SCRIPT ERROR|GPU render" | tail -2
  kill $XVFB 2>/dev/null || true
  echo "B_DONE"
fi
if [ "$1" = "3" ]; then
  ffmpeg -y -loglevel error -threads 2 -i /tmp/p4a.avi -c:v libx264 -preset ultrafast \
    -crf 22 -pix_fmt yuv420p -r 30 $P4/v.mp4
  ffmpeg -y -loglevel error -threads 2 -i /tmp/p4b.avi -c:v libx264 -preset ultrafast \
    -crf 22 -pix_fmt yuv420p -r 30 $P4/phase_04_viseme_lipsync.mp4
  ffmpeg -y -loglevel error -i $P4/fixture.wav -i $P4/v.mp4 -map 0:a -map 1:v \
    -c:a aac -b:a 128k -c:v copy -shortest $P4/phase_04_amplitude_lipsync.mp4
  rm -f $P4/v.mp4 /tmp/p4a.avi /tmp/p4b.avi
  ffmpeg -y -loglevel error -threads 2 -i $P4/phase_04_amplitude_lipsync.mp4 \
    -i $P4/phase_04_viseme_lipsync.mp4 -filter_complex "[0:v][1:v]hstack=inputs=2" \
    -c:v libx264 -preset ultrafast -crf 23 -pix_fmt yuv420p $P4/sbs_v.mp4
  ffmpeg -y -loglevel error -i $P4/fixture.wav -i $P4/sbs_v.mp4 -map 0:a -map 1:v \
    -c:a aac -b:a 128k -c:v copy -shortest $P4/phase_04_comparison_side_by_side.mp4
  rm -f $P4/sbs_v.mp4
  # mouth-open keyframes from B for the contact sheet
  ffmpeg -y -loglevel error -i $P4/phase_04_viseme_lipsync.mp4 -vf \
    "select='eq(n\,55)+eq(n\,180)+eq(n\,400)+eq(n\,640)+eq(n\,820)'" -vsync vfr -frames:v 5 $P4/m_%d.png
  python3 /home/z/my-project/scripts/contact_sheet.py $P4 "m_*.png" $P4/phase_04_contact_sheet.png 3
  rm -f $P4/m_*.png
  ffprobe -v error -show_entries stream=codec_type,codec_name -of csv=p=0 $P4/phase_04_amplitude_lipsync.mp4
  ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1 $P4/phase_04_comparison_side_by_side.mp4
  echo "MUX_DONE"
fi
