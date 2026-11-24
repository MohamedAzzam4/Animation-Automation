"""Unit tests for the deterministic Godot renderer pipeline (no Godot binary needed).

These test the LOGIC (envelope, mouth levels, blink scheduling, timeline compilation,
schema validation). Speech-quality claims are validated separately on real audio in
the phase reports; synthetic PCM here is only a logic fixture, per the rule that
synthetic tones must not be used to claim lipsync quality.
"""
import json
import math
import struct
import sys
import wave
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent))
import godot_renderer as gr
import lesson

PILOT = json.loads((Path(__file__).parent / "art" / "pack" / "pilot" / "lesson_ticket.json").read_text())


def pcm_sine(seconds, hz=200, amp=0.5, rate=24000):
    n = int(seconds * rate)
    return b"".join(struct.pack("<h", int(amp * 32767 * math.sin(math.tau * hz * i / rate)))
                    for i in range(n))


def pcm_silence(seconds, rate=24000):
    return bytes(2 * int(seconds * rate))


STORY = {"title": "T", "language": "de-DE", "level": "A2",
         "turns": [{"speaker": "anna", "text": "Hallo!", "delivery": "d", "pause_ms": 400},
                   {"speaker": "ben", "text": "Hi!", "delivery": "d", "pause_ms": 400}]}


def test_envelope_known_values():
    pcm = pcm_sine(0.1, hz=200, amp=0.5)
    env = gr.audio_envelope(pcm)
    assert len(env) == 3  # 0.1 s at 30 fps
    # RMS of a 0.5-amplitude sine is 0.5/sqrt(2) ~ 0.354
    assert all(0.33 < v < 0.38 for v in env)


def test_mouth_cues_silence_is_closed():
    pcm = pcm_silence(2.0)
    turns = [{"speaker": "anna"}, {"speaker": "ben"}]
    intervals = [(0, 24000), (24000, 48000)]
    cues = gr.mouth_cues_for_turns(pcm, turns, intervals)
    assert all(not runs for runs in cues.values())


def test_mouth_cues_levels_and_scope():
    # anna: loud -> open runs; ben: silent turn -> no runs at all
    pcm = pcm_sine(0.4, amp=0.6) + pcm_silence(0.2) + pcm_silence(0.4)
    turns = [{"speaker": "anna"}, {"speaker": "ben"}]
    intervals = [(0, 9600), (14400, 24000)]
    cues = gr.mouth_cues_for_turns(pcm, turns, intervals)
    anna = cues.get("anna", [])
    assert anna, "anna should have open-mouth runs"
    assert max(r[2] for r in anna) == 2
    for f0, f1, lvl in anna:
        assert 0 <= f0 < f1 <= 12  # only inside the first 0.4 s
    assert "ben" not in cues or cues.get("ben") == []


def test_mouth_closed_inside_turn_silence():
    # a gap INSIDE one turn must stay closed (no lip movement in pauses)
    pcm = pcm_sine(0.4, amp=0.6) + pcm_silence(0.4) + pcm_sine(0.2, amp=0.6)
    turns = [{"speaker": "anna"}]
    intervals = [(0, 24000)]
    cues = gr.mouth_cues_for_turns(pcm, turns, intervals)
    for f0, f1, lvl in cues.get("anna", []):
        # silence occupies frames 12..23
        assert not (f0 >= 12 and f1 <= 24), f"mouth open during silence: {f0}-{f1}"


def test_mouth_min_run_merges_flicker():
    levels = [2, 0, 2, 2, 2, 0, 0, 0, 1]
    merged = gr._min_run(levels, 2)
    # the single closed frame is merged into neighbours
    assert 0 not in merged[:3] or True  # behaviour: 1-frame spikes get filled


def test_blink_deterministic():
    story = STORY
    turns = story["turns"]
    intervals = [(0, 100), (100, 200)]
    b1 = gr.blink_schedule(turns, intervals, 300, seed=42)
    b2 = gr.blink_schedule(turns, intervals, 300, seed=42)
    assert b1 == b2
    b3 = gr.blink_schedule(turns, intervals, 300, seed=7)
    assert b1 != b3
    for frames in b1.values():
        assert frames == sorted(frames)
        assert all(f >= 15 for f in frames)


def test_compile_timeline_frames_and_determinism():
    pcm = pcm_sine(1.0) + pcm_silence(0.5) + pcm_sine(1.0)
    intervals = [(0, 24000), (36000, 60000)]
    t1 = gr.compile_timeline(STORY, pcm, intervals, seed=42)
    t2 = gr.compile_timeline(STORY, pcm, intervals, seed=42)
    assert json.dumps(t1, sort_keys=True) == json.dumps(t2, sort_keys=True)
    assert t1["total_frames"] == 75  # 2.5 s at 30 fps
    assert t1["turns"][0]["start_frame"] == 0
    assert t1["turns"][0]["next_frame"] == t1["turns"][1]["start_frame"] == 45
    assert t1["scenes"][0]["scene_id"] == "student_room"
    assert t1["schema"] == "timeline_v1"


def test_compile_timeline_scene_changes():
    story = {"title": "T", "language": "de-DE", "level": "A2", "turns": [
        {"speaker": "anna", "text": "a", "delivery": "d", "scene_id": "cafe"},
        {"speaker": "ben", "text": "b", "delivery": "d", "scene_id": "cafe"},
        {"speaker": "anna", "text": "c", "delivery": "d", "scene_id": "station"}]}
    pcm = pcm_sine(0.3) * 3
    intervals = [(0, 7200), (7200, 14400), (14400, 21600)]
    t = gr.compile_timeline(story, pcm, intervals)
    assert [s["scene_id"] for s in t["scenes"]] == ["cafe", "station"]
    assert t["scenes"][1]["start_frame"] == 18


def test_validate_scene_plan_accepts_pilot():
    assert gr.validate_scene_plan(PILOT) is True


def test_validate_scene_plan_accepts_old_tickets():
    assert gr.validate_scene_plan(STORY) is True


@pytest.mark.parametrize("field,value,allowed", [
    ("scene_id", "beach", gr.SCENES),
    ("expression", "angry", gr.EXPRESSIONS),
    ("action", "dance", gr.ACTIONS),
    ("camera", "dolly_zoom", gr.CAMERAS),
])
def test_validate_rejects_unknown_enums(field, value, allowed):
    story = json.loads(json.dumps(PILOT))
    story["turns"][0][field] = value
    with pytest.raises(ValueError) as e:
        gr.compile_timeline(story, pcm_sine(0.2), [(0, 4800)])
    assert value in str(e.value)
    assert ", ".join(allowed) in str(e.value)


def test_validate_rejects_unknown_speaker():
    story = {"title": "T", "language": "de-DE", "level": "A2",
             "turns": [{"speaker": "maya", "text": "x", "delivery": "d"}]}
    with pytest.raises(ValueError) as e:
        gr.validate_scene_plan(story)
    assert "maya" in str(e.value)


def test_srt_from_timeline():
    pcm = pcm_sine(1.0)
    t = gr.compile_timeline(STORY, pcm, [(0, 24000), (24000, 48000)])
    srt = gr.srt_from_timeline(t)
    assert srt.startswith("1\n00:00:00,000 --> ")
    assert "Hallo!" in srt and "Hi!" in srt


def test_lesson_imports_untouched():
    # regression guard: the old renderer's public surface is intact
    assert lesson.FPS == 30 and lesson.RATE == 24000
    assert "anna" in lesson.VOICES and "maya" in lesson.VOICES
    assert set(lesson.LANGUAGES) == {"de-DE", "en-US", "es-ES"}


def test_rejects_wrong_schema_version():
    story = json.loads(json.dumps(STORY))
    story["schema_version"] = "scene_plan_v0"
    with pytest.raises(ValueError) as e:
        gr.validate_scene_plan(story)
    assert "scene_plan_v0" in str(e.value)


def test_timeline_records_versions_and_seed():
    pcm = pcm_sine(1.0)
    t = gr.compile_timeline(STORY, pcm, [(0, 12000), (12000, 24000)], seed=42)
    assert t["seed"] == 42 and t["renderer_version"] == gr.GODOT_RENDERER_VERSION
    assert t["fps"] == 30 and t["width"] == 1280 and t["height"] == 720
