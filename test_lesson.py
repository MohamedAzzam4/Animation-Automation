import base64
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import wave

from PIL import Image, ImageFont

import lesson


class LessonTests(unittest.TestCase):
    def test_offline_video_switches_speaker_on_the_measured_frame(self):
        story = json.loads(Path(lesson.__file__).with_name("example.json").read_text(encoding="utf-8"))
        font = ImageFont.truetype(lesson.FONT, 36)
        missing = bytes(font.getmask(chr(0x10FFFF)))
        self.assertTrue(all(bytes(font.getmask(c)) != missing for c in "äöüßñáéíóú¿¡€"))
        with tempfile.TemporaryDirectory() as tmp:
            folder = Path(tmp)
            with patch.object(lesson, "gemini", side_effect=AssertionError("Unexpected network call")):
                video = lesson.render(story, folder, demo=True)
            turns = json.loads((folder / "timeline.json").read_text(encoding="utf-8"))
            self.assertEqual([turn["start_frame"] for turn in turns], [0, 44, 90, 133])
            frames = turns[-1]["next_frame"]
            with wave.open(str(folder / "audio.wav")) as audio:
                self.assertEqual(audio.getnframes(), frames * lesson.SAMPLES_PER_FRAME)
            probe = json.loads(subprocess.check_output([
                "ffprobe", "-v", "error", "-show_entries", "stream=codec_name,nb_frames",
                "-of", "json", str(video),
            ]))
            self.assertEqual([s["codec_name"] for s in probe["streams"]], ["h264", "aac"])
            self.assertEqual(int(probe["streams"][0]["nb_frames"]), frames)
            srt = (folder / "subtitles.srt").read_text(encoding="utf-8")
            self.assertIn("00:00:01,467 --> 00:00:02,485\nGerne. Möchten Sie Zucker?", srt)
            for frame, active in [(0, 0), (43, None), (44, 1)]:
                png = subprocess.check_output([
                    "ffmpeg", "-loglevel", "error", "-i", str(video),
                    "-vf", f"select=eq(n\\,{frame})", "-frames:v", "1", "-threads", "1",
                    "-f", "image2pipe", "-vcodec", "png", "-",
                ])
                with Image.open(io.BytesIO(png)) as img:
                    badge_red = [img.getpixel((x, 553))[1] < 110 for x in (252, 892)]
                self.assertEqual(badge_red, [active == 0, active == 1])

    def test_gemini_speech_request_and_cache(self):
        turn = {"speaker": "anna", "text": "Guten Morgen!", "delivery": "Surprised but friendly"}
        content = {"type": "audio", "data": base64.b64encode(lesson.tone_wav("anna")).decode()}
        result = {"steps": [{"type": "model_output", "content": [content]}]}
        with tempfile.TemporaryDirectory() as tmp:
            with patch.object(lesson, "urlopen", return_value=io.BytesIO(json.dumps(result).encode())) as request:
                args = (turn, "de-DE", "A1", Path(tmp), "fake-key", lesson.TTS_MODEL, False)
                self.assertEqual(lesson.speech_clip(*args), lesson.speech_clip(*args))
                self.assertEqual(request.call_count, 1)
                body = json.loads(request.call_args.args[0].data)
                item = body["input"][0]["content"][0]
                self.assertEqual(item["text"], turn["text"])
                self.assertIn(turn["delivery"], item["annotations"][0]["style"])
                self.assertEqual(body["generation_config"]["speech_config"], [{"voice": "Kore"}])
                self.assertFalse(body["store"])


if __name__ == "__main__":
    unittest.main()
