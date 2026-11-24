extends Node2D
# Timeline-driven deterministic renderer (Main scene).
#
# Input: user args -- --timeline <abs path to timeline_v1.json> [--godot-bin-check]
# Behaviour: _process advances an integer frame counter (Movie Maker --fixed-fps makes
# one _process == one movie frame). ALL state is derived per frame from the timeline:
# current turn, scene, expression, gesture/action, mouth level, blinks, captions.
# No randomness, no deltas. Captions + title live in a screen-space CanvasLayer so
# camera moves (Phase 4) can never occlude them.

var timeline := {}
var frame := 0
var total_frames := 0

var anna: Character2D
var ben: Character2D
var captions: CanvasLayer
var caption_node: Node2D
var bg_cache := {}
var font: Font

const SCENE_BG := {
    "student_room": "res://assets/backgrounds/student_room.png",
    "station": "res://assets/backgrounds/station.png",
    "cafe": "res://assets/backgrounds/cafe.png",
    "riverside_park": "res://assets/backgrounds/riverside_park.png",
}
# two-shot homes (eye anchor positions in world px)
const ANNA_HOME := Vector2(400, 300)
const BEN_HOME := Vector2(880, 300)
const CAPTION_RECT := Rect2(48, 592, 1184, 96)
const NAME_CHIP_Y := 540


func _ready() -> void:
    var args := OS.get_cmdline_user_args()
    var path := ""
    var i := 0
    while i < args.size():
        if args[i] == "--timeline" and i + 1 < args.size():
            path = args[i + 1]
        i += 1
    if path == "":
        push_error("main.gd: --timeline <file> user argument required")
        get_tree().quit(2)
        return
    var raw := FileAccess.get_file_as_string(path)
    timeline = JSON.parse_string(raw)
    if timeline == null or not timeline.has("turns"):
        push_error("main.gd: invalid timeline JSON: " + path)
        get_tree().quit(2)
        return
    total_frames = int(timeline.total_frames)

    # preload every background (never load() during draw)
    for scene_id in SCENE_BG:
        bg_cache[scene_id] = load(SCENE_BG[scene_id])
    font = load("res://assets/fonts/noto-sans-latin.ttf")

    anna = $Anna
    ben = $Ben
    anna.setup("anna")
    ben.setup("ben")
    anna.set_home(ANNA_HOME)
    ben.set_home(BEN_HOME)

    captions = $Captions
    caption_node = captions.get_node("CaptionDraw")
    caption_node.font = font


func _process(_delta: float) -> void:
    if frame >= total_frames:
        get_tree().quit(0)
        return
    _apply_character_states()
    caption_node.set_frame_state(frame, _caption_state())
    queue_redraw()
    caption_node.queue_redraw()
    frame += 1


func _current_turn() -> Dictionary:
    var turns: Array = timeline.turns
    for t in turns:
        if frame >= t.start_frame and frame < t.next_frame:
            return t
    return {}


func _scene_at(frame_idx: int) -> String:
    var current: String = "student_room"
    for s in timeline.scenes:
        if frame_idx >= s.start_frame:
            current = s.scene_id
    return current


func _apply_character_states() -> void:
    var turn := _current_turn()
    var speaking_name := ""
    var a_state := {"expression": "neutral", "look": "right"}
    var b_state := {"expression": "neutral", "look": "left"}
    if not turn.is_empty():
        speaking_name = turn.speaker
        var speaker_state := {
            "expression": turn.expression, "action": turn.action,
            "action_start": int(turn.start_frame), "speaking": true,
        }
        # gesture figure window: first ~2.4 s of the turn; transforms run their
        # natural duration inside set_state
        var gesture := ""
        if str(turn.action) in ["wave", "explain", "point"]:
            gesture = turn.action
        if gesture != "" and frame < int(turn.start_frame) + 72:
            speaker_state["gesture"] = gesture
        var mouth := _mouth_level(speaking_name)
        speaker_state["mouth_level"] = mouth
        if mouth == 0 and frame >= int(turn.end_frame):
            speaker_state["speaking"] = false   # pause after speech: closed mouth
        if speaking_name == "anna":
            a_state.merge(speaker_state, true)
            b_state["expression"] = _listener_expression("ben")
        else:
            b_state.merge(speaker_state, true)
            a_state["expression"] = _listener_expression("anna")
    a_state["blinking"] = _blinking("anna")
    b_state["blinking"] = _blinking("ben")
    anna.set_state(frame, a_state)
    ben.set_state(frame, b_state)


func _listener_expression(name: String) -> String:
    # listener holds the expression of their most recent turn (neutral before it)
    var expr := "neutral"
    for t in timeline.turns:
        if t.speaker == name and frame >= t.start_frame:
            expr = t.expression
    return expr


func _mouth_level(speaker: String) -> int:
    if timeline.has("mouths") and timeline.mouths.has(speaker):
        for run in timeline.mouths[speaker]:
            if frame >= run[0] and frame < run[1]:
                return int(run[2])
    return 0


func _blinking(name: String) -> bool:
    if timeline.has("blinks") and timeline.blinks.has(name):
        for b in timeline.blinks[name]:
            if frame >= b and frame < b + 4:
                return true
    return false


func _caption_state() -> Dictionary:
    var turn := _current_turn()
    var text := ""
    var speaker := ""
    if not turn.is_empty() and frame < int(turn.end_frame):
        text = str(turn.text)
        speaker = str(turn.speaker)
    return {"text": text, "speaker": speaker,
            "title": str(timeline.title), "lang": str(timeline.language),
            "level": str(timeline.level)}


func _draw() -> void:
    var scene_id := _scene_at(frame)
    var bg: Texture2D = bg_cache.get(scene_id)
    if bg:
        draw_texture_rect(bg, Rect2(0, 0, 1280, 720), false)
    # floor shadows under the two-shot homes
    draw_set_transform(Vector2(400, 585), 0, Vector2(1, 0.22))
    draw_circle(Vector2.ZERO, 95, Color(0, 0, 0, 0.20))
    draw_set_transform(Vector2(880, 585), 0, Vector2(1, 0.22))
    draw_circle(Vector2.ZERO, 95, Color(0, 0, 0, 0.20))
    draw_set_transform(Vector2.ZERO, 0, Vector2.ONE)
