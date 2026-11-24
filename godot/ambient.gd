extends Node2D
# Reusable deterministic ambient-effect overlay for the 4 environments.
# Every particle/mote position is a PURE FUNCTION of the absolute frame plus a
# fixed phase table (generated once with random.Random(42) and pasted as constants -
# the engine itself never rolls dice). Optional: set `effect` to "" to disable.

var effect := "dust"

# phase tables (random.Random(42), sampled once at authoring time)
const PHASE := [0.13, 0.71, 0.29, 0.55, 0.91, 0.37, 0.66, 0.03, 0.84, 0.48,
                0.22, 0.59, 0.77, 0.95, 0.08, 0.41, 0.69, 0.17, 0.88, 0.34]
const SIZE := [5.0, 3.5, 7.0, 4.5, 6.0, 3.0, 5.5, 4.0, 6.5, 3.5,
               5.0, 4.5, 3.0, 6.0, 5.5, 4.0, 7.0, 3.5, 5.0, 4.5]
const LEAF_COLOR := Color(0.72, 0.48, 0.18, 0.55)


func _ready() -> void:
    queue_redraw()


func _process(_delta: float) -> void:
    queue_redraw()


func _draw() -> void:
    match effect:
        "dust":
            _dust()
        "clouds":
            _clouds()
        "glow":
            _glow()
        "leaves":
            _leaves()


# student_room: soft dust motes drifting through window light
func _dust() -> void:
    for i in 20:
        var ph: float = PHASE[i]
        var t: float = float(owner_frame())
        var x: float = 180.0 + 900.0 * ph + 14.0 * sin(TAU * (t / 410.0 + ph))
        var y: float = 120.0 + 380.0 * frac(ph * 3.7 + t / (560.0 + 190.0 * ph))
        var a: float = 0.10 + 0.08 * sin(TAU * (t / 173.0 + ph))
        draw_circle(Vector2(x, y), float(SIZE[i]) * 0.8, Color(1.0, 0.95, 0.8, max(0.02, a)))


# station: slow cloud shadows sweeping across the concourse
func _clouds() -> void:
    var t: float = float(owner_frame())
    for i in 3:
        var ph: float = PHASE[i * 3]
        var x: float = frac(ph + t / 5200.0) * 1900.0 - 300.0
        draw_set_transform(Vector2(x, 340.0), 0.0, Vector2(1.0, 0.30))
        draw_circle(Vector2.ZERO, 260.0 + 60.0 * ph, Color(0.10, 0.12, 0.16, 0.055))
    draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)


# cafe: warm light breathing + rising steam wisps near the right table area
func _glow() -> void:
    var t: float = float(owner_frame())
    var a: float = 0.05 + 0.022 * sin(TAU * t / 240.0)
    draw_rect(Rect2(0, 0, 1280, 720), Color(1.0, 0.78, 0.42, a))
    for i in 4:
        var ph: float = PHASE[i + 6]
        var x: float = 940.0 + 24.0 * i
        var y: float = 470.0 - 130.0 * frac(ph + t / (410.0 + 60.0 * i))
        var r: float = 9.0 + 5.0 * frac(ph + t / 300.0)
        draw_circle(Vector2(x, y), r, Color(1.0, 1.0, 1.0, 0.045))


# riverside_park: golden-hour leaves drifting down on lissajous paths
func _leaves() -> void:
    var t: float = float(owner_frame())
    for i in 7:
        var ph: float = PHASE[i + 1]
        var speed: float = 0.9 + 0.5 * ph
        var y: float = 40.0 + 690.0 * frac(ph * 2.3 + t * speed / 620.0)
        var x: float = 120.0 + 1040.0 * ph + 36.0 * sin(TAU * (t / 260.0 + ph * 3.0))
        var sway: float = 0.35 + 0.3 * sin(TAU * (t / 97.0 + ph))
        draw_set_transform(Vector2(x, y), sway, Vector2(1.0, 0.55))
        draw_colored_polygon(PackedVector2Array([Vector2(-8, 0), Vector2(0, -4),
            Vector2(8, 0), Vector2(0, 4)]), LEAF_COLOR)
    draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)


func frac(v: float) -> float:
    return v - floor(v)


func owner_frame() -> int:
    var parent := get_parent()
    if parent and parent.has_method("current_frame"):
        return parent.current_frame()
    return 0
