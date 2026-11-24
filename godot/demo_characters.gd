extends Node2D
# Phase 2 acceptance demo: 10 s (300 frames @ 30 fps) showing Anna and Ben with
# idle breathing, scheduled blinks, expression swaps, look direction, speech
# mouths and one gesture each. Hardcoded deterministic schedule; the real
# timeline arrives in Phase 5. Rendered via Movie Maker.

const DEMO_FRAMES := 300

var anna: Character2D
var ben: Character2D
var frame := 0

# deterministic blink schedules (seeded at compile time in the real pipeline;
# here fixed constants for the demo)
const ANNA_BLINKS := [22, 58, 97, 141, 190, 236, 281]
const BEN_BLINKS := [35, 74, 118, 163, 205, 252, 291]


func _ready() -> void:
    anna = $Anna
    ben = $Ben
    anna.setup("anna")
    ben.setup("ben")
    anna.set_home(Vector2(400, 300))
    ben.set_home(Vector2(880, 300))


func _process(_delta: float) -> void:
    frame += 1
    if frame > DEMO_FRAMES:
        get_tree().quit(0)
        return
    _apply(anna, _anna_state(frame), ANNA_BLINKS)
    _apply(ben, _ben_state(frame), BEN_BLINKS)
    queue_redraw()


func _blinking(frame: int, blinks: Array) -> bool:
    for b in blinks:
        if frame >= b and frame < b + 4:
            return true
    return false


func _apply(ch: Character2D, state: Dictionary, blinks: Array) -> void:
    state["blinking"] = _blinking(frame, blinks)
    ch.set_state(frame, state)


# deterministic speech mouth pattern for the demo (quarter-second syllables)
func _demo_mouth(frame: int, start: int, end: int) -> int:
    if frame < start or frame >= end:
        return 0
    var k := (frame - start) % 12
    if k < 4:
        return 2
    if k < 7:
        return 1
    return 0


func _anna_state(f: int) -> Dictionary:
    # 0-90 idle neutral; 90-180 happy speaking; 180-240 wave; 240-300 thinking
    if f < 90:
        return {"expression": "neutral", "look": "right", "action": "idle"}
    if f < 180:
        return {"expression": "happy", "speaking": true,
                "mouth_level": _demo_mouth(f, 96, 174)}
    if f < 240:
        return {"expression": "happy", "gesture": "wave", "action": "wave",
                "action_start": 180}
    return {"expression": "thinking", "look": "right", "action": "idle"}


func _ben_state(f: int) -> Dictionary:
    # 0-120 neutral listening; 120-210 thinking (head tilt); 210-300 explain gesture
    if f < 120:
        return {"expression": "neutral", "look": "left", "action": "idle"}
    if f < 210:
        return {"expression": "thinking", "look": "left", "action": "head_tilt",
                "action_start": 120}
    return {"expression": "neutral", "gesture": "explain", "action": "explain",
            "action_start": 210}


func _draw() -> void:
    var bg: Texture2D = load("res://assets/backgrounds/student_room.png")
    draw_texture_rect(bg, Rect2(0, 0, 1280, 720), false)
    # soft floor shadows under the characters
    draw_set_transform(Vector2(400, 560), 0, Vector2(1, 0.22))
    draw_circle(Vector2.ZERO, 90, Color(0, 0, 0, 0.18))
    draw_set_transform(Vector2(880, 560), 0, Vector2(1, 0.22))
    draw_circle(Vector2.ZERO, 90, Color(0, 0, 0, 0.18))
    draw_set_transform(Vector2.ZERO, 0, Vector2.ONE)
    draw_string(ThemeDB.fallback_font, Vector2(24, 40),
        "Phase 2 demo: Anna & Ben composite-bust controller", HORIZONTAL_ALIGNMENT_LEFT, -1, 24)
