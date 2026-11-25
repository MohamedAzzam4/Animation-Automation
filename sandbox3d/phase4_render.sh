#!/bin/bash
# Render both Phase 4 lip-sync reels + side-by-side, with audio muxed.
set -e
GODOT=/home/z/my-project/work/tools/godot/Godot_v4.7.2-stable_linux.x86_64
PROJ=/home/z/my-project/work/language-video-workflow/godot3d
P4=/home/z/my-project/work/language-video-workflow/output3d/phase4
export HOME=/home/z

DISPLAY_NUM=112
while [ -e /tmp/.X11-unix/X$DISPLAY_NUM ]; do DISPLAY_NUM=$((DISPLAY_NUM+1)); done
Xvfb :$DISPLAY_NUM -screen 0 1280x720x24 -nolisten tcp 2>/dev/null &
XVFB=$!
sleep 1
export DISPLAY=:$DISPLAY_NUM

"$GODOT" --path "$PROJ" --rendering-driver opengl3 --write-movie /tmp/p4a.avi \
  --fixed-fps 30 --quit-after 922 "$PROJ/phase4_lipsync.tscn" -- \
  --sched=$P4/amplitude_schedule.json --log=$P4/amplitude_driver_log.csv \
  --label=Method_A_amplitude > /tmp/p4a.log 2>&1
"$GODOT" --path "$PROJ" --rendering-driver opengl3 --write-movie /tmp/p4b.avi \
  --fixed-fps 30 --quit-after 922 "$PROJ/phase4_lipsync.tscn" -- \
  --sched=$P4/viseme_schedule.json --log=$P4/viseme_driver_log.csv \
  --label=Method_B_phoneme_viseme > /tmp/p4b.log 2>&1
kill $XVFB 2>/dev/null || true

ffmpeg -y -loglevel error -threads 2 -i /tmp/p4a.avi -c:v libx264 -preset ultrafast \
  -crf 22 -pix_fmt yuv420p -r 30 $P4/v.mp4
ffmpeg -y -loglevel error -threads 2 -i /tmp/p4b.avi -c:v libx264 -preset ultrafast \
  -crf 22 -pix_fmt yuv420p -r 30 $P4/phase_04_viseme_lipsync.mp4
ffmpeg -y -loglevel error -i $P4/fixture.wav -i $P4/v.mp4 -map 0:a -map 1:v \
  -c:a aac -b:a 128k -c:v copy -shortest $P4/phase_04_amplitude_lipsync.mp4
rm $P4/v.mp4
ffmpeg -y -loglevel error -threads 2 -i $P4/phase_04_amplitude_lipsync.mp4 \
  -i $P4/phase_04_viseme_lipsync.mp4 -filter_complex "[0:v][1:v]hstack=inputs=2" \
  -c:v libx264 -preset ultrafast -crf 23 -pix_fmt yuv420p $P4/sbs_v.mp4
ffmpeg -y -loglevel error -i $P4/fixture.wav -i $P4/sbs_v.mp4 -map 0:a -map 1:v \
  -c:a aac -b:a 128k -c:v copy -shortest $P4/phase_04_comparison_side_by_side.mp4
rm $P4/sbs_v.mp4
echo DONE
ffprobe -v error -show_entries stream=codec_type,codec_name -of csv=p=0 $P4/phase_04_amplitude_lipsync.mp4
ffprobe -v error -show_entries stream=codec_type,codec_name -of csv=p=0 $P4/phase_04_viseme_lipsync.mp4
