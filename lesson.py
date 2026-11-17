"""Generate a language lesson and render its timed dialogue to MP4."""

import argparse
import base64
import hashlib
import io
import json
import math
import os
from pathlib import Path
import shutil
import struct
import subprocess
import tempfile
import textwrap
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen
import wave

from PIL import Image, ImageDraw, ImageFont, ImageOps


ASSETS = Path(__file__).resolve().parent / "assets"
FONT = ASSETS / "noto-sans-latin.ttf"
VOICES = {"anna": "Kore", "maya": "Aoede", "ben": "Puck", "martin": "Charon"}
LANGUAGES = {
    "de-DE": "standard German as spoken in Germany",
    "en-US": "standard American English",
    "es-ES": "standard Spanish as spoken in Spain",
}
LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
MODES = ("auto", "dialogue", "narration", "mixed")
API = "https://generativelanguage.googleapis.com/v1beta/interactions"
TEXT_MODEL = "gemini-3.5-flash-lite"
TTS_MODEL = "gemini-3.8-flash-lite-tts"
WIDTH, HEIGHT, FPS, RATE = 1280, 720, 30, 24000
SAMPLES_PER_FRAME = RATE // FPS
TEXT_LIMIT = 120
MAX_TURNS = 30


def object_schema(**properties):
    return {"type": "object", "properties": properties, "required": list(properties)}


SCHEMA = object_schema(
    title={"type": "string"},
    turns={"type": "array", "items": object_schema(
        speaker={"type": "string", "enum": list(VOICES)},
        text={"type": "string"},
        delivery={"type": "string"},
        pause_ms={"type": "integer"},
    )},
)


def gemini(key, kind, **body):
    request = Request(
        API, data=json.dumps({"store": False, **body}).encode("utf-8"),
        headers={"Content-Type": "application/json", "x-goog-api-key": key,
                 "Api-Revision": "2026-05-20"},
    )
    try:
        with urlopen(request, timeout=120) as response:
            result = json.load(response)
    except HTTPError as exc:
        if exc.code in (401, 403):
            hint = " Check the key and its Gemini Developer API access."
        elif exc.code == 429:
            hint = " Quota or rate limit reached. Wait and resume using the saved script."
        else:
            hint = " Check model availability and the project's API settings."
        raise RuntimeError(f"Gemini {kind} request failed (HTTP {exc.code}).{hint}") from exc
    except (URLError, TimeoutError) as exc:
        raise RuntimeError("Could not reach Gemini. Check the network and retry.") from exc
    blocks = [
        block
        for step in result.get("steps", [])
        if step.get("type") == "model_output"
        for block in step.get("content", [])
        if block.get("type") == kind
    ]
    if not blocks:
        raise RuntimeError(f"Gemini returned no {kind} output (status: {result.get('status', 'unknown')}).")
    return blocks[-1]


def write_story(topic, language, level, mode, count, key, model):
    formats = {
        "auto": "Choose narration, dialogue, or a mix based on the topic.",
        "narration": "Every turn is spoken by martin alone.",
        "dialogue": "Use two or three of anna, ben, and maya. Do not use martin.",
        "mixed": "Use martin for narration and at least two other people for dialogue.",
    }
    prompt = (
        f"Write a short, coherent {level} CEFR language-learning story in {LANGUAGES[language]}. "
        f"Topic: {json.dumps(topic, ensure_ascii=False)}. {formats[mode]} "
        f"Make exactly {count} speaking turns. Use natural everyday spoken language. "
        "For A1/A2, favor high-frequency vocabulary, short sentences, and concrete situations. "
        "Use martin only as narrator, and anna, ben, or maya as dialogue characters. "
        f"Each spoken turn is at most {TEXT_LIMIT} characters. No speaker names, markup, or directions in text. "
        "Write a short title, up to 64 characters. Give each turn a short delivery direction in English "
        "describing the appropriate emotion or tone, and a pause_ms of about 350 to 650."
    )
    block = gemini(key, "text", model=model, input=prompt,
                   response_format={"type": "text", "mime_type": "application/json", "schema": SCHEMA})
    story = json.loads(block["text"])
    if not isinstance(story, dict):
        raise ValueError("Gemini returned an invalid script.")
    story.update(language=language, level=level)
    validate_story(story)
    speakers = {turn["speaker"] for turn in story["turns"]}
    others = speakers - {"martin"}
    mode_ok = {
        "auto": True,
        "narration": speakers == {"martin"},
        "dialogue": "martin" not in speakers and len(others) >= 2,
        "mixed": "martin" in speakers and len(others) >= 2,
    }
    if len(story["turns"]) != count or not mode_ok[mode]:
        raise ValueError("Generated story did not match the requested format or turn count. Try again.")
    return story


def clean_string(value, limit):
    return isinstance(value, str) and 0 < len(value) <= limit and bool(value.strip()) and value.isprintable()


def validate_story(story):
    if not isinstance(story, dict) or not clean_string(story.get("title"), 64):
        raise ValueError("Script needs a title of 1 to 64 characters.")
    if story.get("language") not in tuple(LANGUAGES) or story.get("level") not in LEVELS:
        raise ValueError("Script needs a supported language and CEFR level.")
    turns = story.get("turns")
    if not isinstance(turns, list) or not 1 <= len(turns) <= MAX_TURNS:
        raise ValueError(f"Script needs 1 to {MAX_TURNS} speaking turns.")
    for number, turn in enumerate(turns, 1):
        if not isinstance(turn, dict) or turn.get("speaker") not in tuple(VOICES):
            raise ValueError(f"Turn {number}: invalid speaker ID.")
        if not clean_string(turn.get("text"), TEXT_LIMIT) or any(c in turn["text"] for c in "<>"):
            raise ValueError(f"Turn {number}: use 1 to {TEXT_LIMIT} characters of plain speech.")
        if not clean_string(turn.get("delivery"), 120):
            raise ValueError(f"Turn {number}: add a short delivery direction.")
        pause = turn.get("pause_ms", 400)
        if type(pause) is not int or not 0 <= pause <= 3000:
            raise ValueError(f"Turn {number}: pause_ms must be an integer between 0 and 3000.")


def read_pcm(wav_bytes):
    with wave.open(io.BytesIO(wav_bytes), "rb") as source:
        if (source.getframerate(), source.getsampwidth(), source.getnchannels()) != (RATE, 2, 1):
            raise ValueError("Expected Gemini's 24 kHz mono 16-bit WAV output.")
        frames = source.getnframes()
        pcm = source.readframes(frames)
        if not frames or len(pcm) != frames * 2:
            raise ValueError("Gemini returned an empty or incomplete WAV clip.")
        return pcm


def tone_wav(speaker):
    """Offline timing fixture. Deliberately not a synthetic voice."""
    hz = 260 + 90 * list(VOICES).index(speaker)
    count = RATE + hz
    raw = b"".join(struct.pack("<h", int(2300 * math.sin(math.tau * hz * i / RATE)))
                   for i in range(count))
    stream = io.BytesIO()
    with wave.open(stream, "wb") as wav:
        wav.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
        wav.writeframes(raw)
    return stream.getvalue()


def speech_clip(turn, language, level, folder, key, model, demo):
    voice = VOICES[turn["speaker"]]
    pace = "an unhurried pace with clear articulation" if level in ("A1", "A2") else "a natural pace"
    style = f"{turn['delivery'].strip()}. Use {LANGUAGES[language]} and {pace}."
    cache_key = json.dumps([model, voice, style, turn["text"]], ensure_ascii=False)
    prefix = "demo" if demo else "tts"
    path = folder / f"{prefix}-{hashlib.sha256(cache_key.encode()).hexdigest()[:24]}.wav"
    if path.is_file():
        return read_pcm(path.read_bytes())
    if demo:
        wav_bytes = tone_wav(turn["speaker"])
    else:
        block = gemini(
            key, "audio", model=model, response_format={"type": "audio"},
            generation_config={"speech_config": [{"voice": voice}]},
            input=[{"type": "user_input", "content": [{
                "type": "text", "text": turn["text"].strip(),
                "annotations": [{"type": "speech_metadata", "style": style}],
            }]}],
        )
        wav_bytes = base64.b64decode(block["data"], validate=True)
    pcm = read_pcm(wav_bytes)
    partial = path.with_suffix(".tmp")
    partial.write_bytes(wav_bytes)
    partial.replace(path)
    return pcm


def make_card(background, portraits, story, speakers, speaker=None, caption=None):
    card = background.copy()
    draw = ImageDraw.Draw(card)
    ink, cream, active_color = "#37251F", "#FFF5E4", "#A13B25"
    shown = ["martin"] if speaker == "martin" and len(speakers) > 1 else [
        name for name in speakers if name != "martin" or len(speakers) == 1
    ]
    draw.rounded_rectangle((48, 37, 916, 100), radius=24, fill=cream)
    title = story["title"].strip()
    title_font = ImageFont.truetype(FONT, 33)
    if title_font.getlength(title) > 810:
        title_font = ImageFont.truetype(FONT, int(33 * 810 / title_font.getlength(title)))
    draw.text((75, 68), title, font=title_font, fill=ink, anchor="lm")
    draw.rounded_rectangle((1006, 37, 1232, 100), radius=24, fill=ink)
    draw.text((1119, 68), f"{story['language']}  /  {story['level']}",
              font=ImageFont.truetype(FONT, 24), fill=cream, anchor="mm")
    for index, name in enumerate(shown):
        center = int((index + 0.5) * WIDTH / len(shown))
        portrait = ImageOps.contain(portraits[name], (min(415, WIDTH // len(shown) - 58), 425))
        active = speaker == name and caption is not None
        if active:
            draw.ellipse((center - 148, 126, center + 148, 430), fill="#FFF0CA")
        card.paste(portrait, (center - portrait.width // 2, 557 - portrait.height), portrait)
        draw.rounded_rectangle((center - 83, 530, center + 83, 575), radius=20,
                               fill=active_color if active else cream)
        draw.text((center, 552), name.title(), font=ImageFont.truetype(FONT, 23),
                  fill=cream if active else ink, anchor="mm")
    draw.rounded_rectangle((48, 592, 1232, 688), radius=24, fill=ink)
    if caption:
        lines = textwrap.wrap(caption, width=47)
        size = 36 if len(lines) < 3 else 26
        font = ImageFont.truetype(FONT, size)
        longest = max(font.getlength(line) for line in lines)
        if longest > 1100:
            font = ImageFont.truetype(FONT, int(size * 1100 / longest))
        draw.multiline_text((WIDTH // 2, 640), "\n".join(lines), font=font,
                            fill=cream, anchor="mm", align="center", spacing=3)
    return card


def srt_time(ms):
    seconds, millis = divmod(ms, 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    return f"{hours:02}:{minutes:02}:{seconds:02},{millis:03}"


def render(story, output, key=None, model=TTS_MODEL, demo=False):
    validate_story(story)
    output.mkdir(parents=True, exist_ok=True)
    clips = output / "clips"
    clips.mkdir(exist_ok=True)
    (output / "script.json").write_text(json.dumps(story, ensure_ascii=False, indent=2) + "\n",
                                        encoding="utf-8")
    speakers = [name for name in VOICES if any(t["speaker"] == name for t in story["turns"])]
    background = Image.open(ASSETS / "warm-background.webp").convert("RGB")
    portraits = {name: Image.open(ASSETS / f"{name}.webp").convert("RGBA") for name in speakers}
    sections, subtitles, timeline = [], [], []
    frame = 0
    with tempfile.TemporaryDirectory(prefix=".render-", dir=output) as temporary:
        temp = Path(temporary)
        with wave.open(str(temp / "audio.wav"), "wb") as track:
            track.setparams((1, 2, RATE, 0, "NONE", "not compressed"))
            for number, turn in enumerate(story["turns"], 1):
                print(f"Turn {number}/{len(story['turns'])} · {turn['speaker']}", flush=True)
                pcm = speech_clip(turn, story["language"], story["level"], clips, key, model, demo)
                speech_samples = len(pcm) // 2
                on = (speech_samples + SAMPLES_PER_FRAME - 1) // SAMPLES_PER_FRAME
                pause_samples = turn.get("pause_ms", 400) * RATE // 1000
                span = (speech_samples + pause_samples + SAMPLES_PER_FRAME - 1) // SAMPLES_PER_FRAME
                track.writeframesraw(pcm)
                track.writeframesraw(bytes(2 * (span * SAMPLES_PER_FRAME - speech_samples)))

                # ponytail: whole-turn stills; add animation only if the pilot needs it.
                still = f"{number:03}.png"
                make_card(background, portraits, story, speakers, turn["speaker"], turn["text"]).save(temp / still)
                sections.append((still, on))
                if span > on:
                    silent = f"{number:03}-pause.png"
                    make_card(background, portraits, story, speakers,
                              "martin" if turn["speaker"] == "martin" else None).save(temp / silent)
                    sections.append((silent, span - on))

                start_ms = round(frame * 1000 / FPS)
                end_ms = max(start_ms + 1, round((frame * SAMPLES_PER_FRAME + speech_samples) * 1000 / RATE))
                subtitles.append(f"{number}\n{srt_time(start_ms)} --> {srt_time(end_ms)}\n{turn['text']}")
                timeline.append({"speaker": turn["speaker"], "text": turn["text"],
                                 "start_ms": start_ms, "end_ms": end_ms,
                                 "start_frame": frame, "next_frame": frame + span})
                frame += span

        last = sections[-1][0]
        concat = "ffconcat version 1.0\n" + "".join(
            f"file {filename}\noption framerate {FPS}\nduration {length / FPS:.9f}\n"
            for filename, length in sections
        ) + f"file {last}\noption framerate {FPS}\n"
        (temp / "frames.ffconcat").write_text(concat, encoding="ascii")
        subprocess.run(
            ["ffmpeg", "-hide_banner", "-loglevel", "error", "-nostdin",
             "-f", "concat", "-safe", "0", "-i", "frames.ffconcat", "-i", "audio.wav",
             "-vf", f"fps={FPS}", "-t", f"{frame / FPS:.9f}",
             "-c:v", "libx264", "-preset", "fast", "-crf", "20", "-pix_fmt", "yuv420p",
             "-c:a", "aac", "-movflags", "+faststart", "video.mp4"],
            cwd=temp, check=True,
        )
        (temp / "video.mp4").replace(output / "video.mp4")
        (temp / "audio.wav").replace(output / "audio.wav")
    (output / "subtitles.srt").write_text("\n\n".join(subtitles) + "\n", encoding="utf-8")
    (output / "timeline.json").write_text(json.dumps(timeline, ensure_ascii=False, indent=2) + "\n",
                                          encoding="utf-8")
    return output / "video.mp4"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--topic", help="Ask Gemini to write the script from this topic.")
    source.add_argument("--script", type=Path, help="Render an existing JSON script.")
    parser.add_argument("--language", choices=LANGUAGES, default="de-DE")
    parser.add_argument("--level", choices=LEVELS, default="A1")
    parser.add_argument("--mode", choices=MODES, default="auto")
    parser.add_argument("--turns", type=int, choices=range(1, MAX_TURNS + 1), default=12, metavar="1–30")
    parser.add_argument("--output", type=Path, default=Path("output"))
    parser.add_argument("--text-model", default=TEXT_MODEL)
    parser.add_argument("--tts-model", default=TTS_MODEL)
    parser.add_argument("--demo", action="store_true", help="Use offline test tones with --script.")
    args = parser.parse_args()
    if args.demo and not args.script:
        parser.error("--demo requires --script and never calls Gemini.")
    if args.topic is not None and not args.topic.strip():
        parser.error("--topic cannot be empty.")
    if args.topic and args.turns < {"dialogue": 2, "mixed": 3}.get(args.mode, 1):
        parser.error("Dialogue needs at least 2 turns, and mixed needs at least 3.")
    if not shutil.which("ffmpeg"):
        parser.error("Install FFmpeg and put it on PATH.")
    key = os.environ.get("GEMINI_API_KEY")
    if not args.demo and not key:
        parser.error("Set GEMINI_API_KEY in your environment, or use --demo with a script.")
    try:
        story = (json.loads(args.script.read_text(encoding="utf-8")) if args.script else
                 write_story(args.topic, args.language, args.level, args.mode, args.turns, key, args.text_model))
        target = render(story, args.output, key, args.tts_model, args.demo)
    except (OSError, ValueError, RuntimeError, wave.Error, KeyError, EOFError,
            subprocess.CalledProcessError) as error:
        parser.exit(1, f"Error: {error}\n")
    print(f"Exported {target}")


if __name__ == "__main__":
    main()
