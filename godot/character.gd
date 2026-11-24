extends Node2D
class_name Character2D
# Deterministic composite-bust character controller.
#
# Contract: all visual state is a PURE FUNCTION of (absolute frame, state dict).
# No randomness, no time deltas. The timeline evaluator (main.gd / demo) calls
# set_state(frame, state) once per frame; this node derives everything else.
#
# State keys: expression, gesture, mouth_level, blinking, look, action,
#             action_start, speaking
#
# Assets: all textures for one character share a single canvas size and are
# anchored at the eye midpoint (node origin == eye anchor), so expression and
# gesture swaps can never move the head. DESIGN RULE from Phase 1: textures are
# preloaded in setup(); load() is never called during draw/process.

const EXPR := ["neutral", "happy", "surprised", "thinking", "worried"]
const BLINK_FRAMES := 4
const NOD_FRAMES := 36
const TILT_FRAMES := 54
const GESTURE_SWAY_PERIOD := 45

var character_id := ""
var canvas := Vector2.ZERO
var _tex := {}
var _cur_base_path := ""
var _cur_ov_path := ""

@onready var body: Sprite2D = $Body
@onready var overlay: Sprite2D = $Overlay


func setup(id: String) -> void:
    character_id = id
    var manifest: Dictionary = JSON.parse_string(
        FileAccess.get_file_as_string("res://assets/characters/%s/manifest.json" % id))
    canvas = Vector2(manifest.canvas[0], manifest.canvas[1])
    for f in manifest.files:
        _tex[f] = load("res://assets/characters/%s/%s" % [id, f])
    # both sprites are drawn from the top-left of the shared canvas, so the node
    # origin sits at the eye anchor
    for s in [body, overlay]:
        s.centered = false
        s.position = -Vector2(manifest.eye_anchor[0], manifest.eye_anchor[1])
    # reference portrait kept out of the animation set
    _tex.erase("reference_canonical.png")
    set_state(0, {})


func set_state(frame: int, state: Dictionary) -> void:
    var expression: String = state.get("expression", "neutral")
    if not EXPR.has(expression):
        expression = "neutral"
    var gesture: String = state.get("gesture", "")
    var mouth: int = clampi(int(state.get("mouth_level", 0)), 0, 2)
    var blinking: bool = state.get("blinking", false)
    var look: String = state.get("look", "")
    var speaking: bool = state.get("speaking", false)
    var action: String = state.get("action", "")
    var action_start: int = int(state.get("action_start", -1))

    # ---- base + overlay texture choice (steady anchors by construction) ----
    var base_path := ""
    var ov_path := ""
    if gesture != "" and _tex.has("gesture_%s.png" % gesture):
        base_path = "gesture_%s.png" % gesture
    elif speaking:
        base_path = "expr_%s_noMouth.png" % expression
        ov_path = "expr_%s_mouth%d.png" % [expression, mouth]
    else:
        base_path = "expr_%s.png" % expression
    if base_path != "" and base_path != _cur_base_path:
        body.texture = _tex[base_path]
        _cur_base_path = base_path
    var look_ok := look == "left" or look == "right"
    if gesture == "" and not speaking and blinking and _tex.has("expr_%s_blink.png" % expression):
        ov_path = "expr_%s_blink.png" % expression
    elif gesture == "" and not speaking and look_ok and _tex.has("expr_%s_look%s.png" % [expression, look]):
        ov_path = "expr_%s_look%s.png" % [expression, look]
    if ov_path != _cur_ov_path:
        overlay.texture = _tex.get(ov_path)
        _cur_ov_path = ov_path

    # ---- transforms: pure functions of absolute frame ----
    var t := float(frame)
    # idle breathing: 3.7 s period, 2 px bob + 0.4% scale pulse around the eye anchor
    var breathe := TAU * t / 111.0
    var pos := Vector2(0.0, 2.0 * sin(breathe))
    var rot := 0.0
    var scl := 1.0 + 0.004 * sin(breathe)
    if gesture != "":
        # gentle conversational sway while the gesture sticker is shown
        rot += 0.03 * sin(TAU * t / GESTURE_SWAY_PERIOD)
    var in_nod := action == "nod" and action_start >= 0 and frame >= action_start and frame < action_start + NOD_FRAMES
    var in_tilt := action == "head_tilt" and action_start >= 0 and frame >= action_start and frame < action_start + TILT_FRAMES
    if in_nod:
        var k := float(frame - action_start) / NOD_FRAMES
        pos.y += 2.5 * abs(sin(PI * k))
        rot += 0.02 * sin(TAU * k)
    elif in_tilt:
        var k2 := float(frame - action_start) / TILT_FRAMES
        rot += 0.06 * sin(PI * k2)   # ease in and out, peak ~3.4 deg
    position = pos + _home
    rotation = rot
    scale = Vector2(scl, scl)


var _home := Vector2.ZERO

func set_home(p: Vector2) -> void:
    _home = p
    position = p


func head_anchor() -> Vector2:
    return _home
