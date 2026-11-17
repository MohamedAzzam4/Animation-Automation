# Language Video Workflow

Make a language-learning video from a topic or an existing script. Python runs the entire pipeline. No n8n, web server, or video generation API.

## Implementation plan

1. Use Gemini to write a short story at the requested CEFR level, or load an existing JSON script. Validate the text, speaker IDs, and delivery directions.
2. Assign fixed voices and portraits to Anna, Ben, Maya, and Martin. Ask Gemini TTS to perform one turn at a time, passing delivery instructions separately from the spoken text. Save and reuse identical WAV clips.
3. Derive one timeline from the exact audio sample counts. Concatenate speech and pauses, highlight the active portrait, and show its caption over the same warm background in every video.
4. Export an MP4 with burned-in captions, a separate SRT, and the audio and timings for reuse. Verify the renderer offline before running a real voice test.

## Run

Requires Python 3.10+ and FFmpeg with `libx264` on PATH. Install in a virtual environment if preferred.

```sh
python -m pip install -r requirements.txt
# Offline check. The audio is test tones, not spoken words.
python lesson.py --script example.json --demo --output output/demo
```

For real speech, set `GEMINI_API_KEY` in your shell or runtime secrets. One [Google AI Studio API key](https://aistudio.google.com/apikey) is enough for writing and speech. Don't put the key in the repo.

```sh
# Test real TTS without a separate story-writing request.
python lesson.py --script example.json --output output/cafe

# Generate a script and render it.
python lesson.py --topic "Buying a train ticket" --language de-DE --level A1 --mode auto --output output/train

# Narrator only.
python lesson.py --topic "A lost dog finds its way home" --language en-US --level A2 --mode narration --output output/dog
```

`--language` accepts `de-DE`, `en-US`, and `es-ES`. `--level` accepts A1–C2. `--mode` can be `auto`, `dialogue`, `narration`, or `mixed`. Use `--turns` to choose the number of speaking turns when generating a story. The default models are Gemini 3.5 Flash-Lite for writing and Gemini 3.8 Flash-Lite TTS for speech. Try `--tts-model gemini-3.8-flash-tts` for comparison if your key has access.

The output folder contains `video.mp4`, `audio.wav`, `subtitles.srt`, `script.json`, `timeline.json`, and individual WAVs in `clips/`. To resume after an API limit or fix one take, edit or reuse the saved script and run with `--script path/to/script.json` and the **same** output folder. Unchanged lines are cached. Timing is rounded up by less than one video frame between turns.

Portraits and the reusable backdrop are in `assets/`. The renderer uses still portraits with speaker highlights. It doesn't generate new imagery for each topic.

## Check

```sh
python -m unittest -v
```

The tests need FFmpeg and ffprobe. They check timing, captions, speaker changes, the TTS request structure, and caching without sending API requests.
