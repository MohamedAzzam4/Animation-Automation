extends Node2D
# Screen-space caption/title layer (drawn above the world; camera-independent).

var font: Font
var state := {"text": "", "speaker": "", "title": "", "lang": "", "level": ""}

const INK := Color("37251f")
const CREAM := Color("fff5e4")
const ACCENT := Color("a13b25")
const CAPTION_RECT := Rect2(48, 592, 1184, 96)


func set_frame_state(_frame: int, new_state: Dictionary) -> void:
    state = new_state


func _draw() -> void:
    # title bar
    _panel(Rect2(48, 37, 916, 63), 24, CREAM)
    _text(str(state.get("title", "")), Vector2(75, 68), 31, INK, 810)
    _panel(Rect2(1006, 37, 226, 63), 24, INK)
    var badge := "%s  /  %s" % [state.get("lang", ""), state.get("level", "")]
    _centered(badge, Rect2(1006, 37, 226, 63), 22, CREAM)
    # name chips
    _name_chip(Vector2(400, 540), "Anna", state.get("speaker", "") == "anna")
    _name_chip(Vector2(880, 540), "Ben", state.get("speaker", "") == "ben")
    # caption box
    var text := str(state.get("text", ""))
    if text != "":
        _panel(CAPTION_RECT, 24, INK)
        var lines := _wrap(text, 38, CAPTION_RECT.size.x - 96)
        var size := 36 if lines.size() < 3 else 26
        var spacing := 3
        var total_h := lines.size() * (size + spacing)
        var y := CAPTION_RECT.position.y + (CAPTION_RECT.size.y - total_h) / 2.0 + size * 0.75
        for line in lines:
            _centered(line, Rect2(CAPTION_RECT.position.x, y - size, CAPTION_RECT.size.x, size * 1.3), size, CREAM)
            y += size + spacing


func _panel(rect: Rect2, radius: int, fill: Color) -> void:
    var style := StyleBoxFlat.new()
    style.bg_color = fill
    style.set_corner_radius_all(radius)
    draw_style_box(style, rect)


func _text(s: String, pos: Vector2, size: int, color: Color, max_w: float = 0) -> void:
    if s == "":
        return
    var use_size := size
    if max_w > 0:
        var w := font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
        if w > max_w:
            use_size = int(size * max_w / w)
    draw_string(font, pos, s, HORIZONTAL_ALIGNMENT_LEFT, -1, use_size, color)


func _centered(s: String, rect: Rect2, size: int, color: Color) -> void:
    # draw_string only honours alignment inside a real width; pass the target rect
    draw_string(font, Vector2(rect.position.x, rect.position.y + rect.size.y), s,
        HORIZONTAL_ALIGNMENT_CENTER, rect.size.x, size, color)


func _name_chip(center: Vector2, name: String, active: bool) -> void:
    var rect := Rect2(center.x - 83, center.y - 22, 166, 44)
    _panel(rect, 20, ACCENT if active else CREAM)
    _centered(name, rect, 22, CREAM if active else INK)


func _wrap(text: String, max_chars: int, max_width: float) -> Array:
    var words := text.split(" ", false)
    var lines: Array = []
    var line := ""
    for w in words:
        var candidate := (line + " " + w).strip_edges()
        if candidate.length() > max_chars or (line != "" and _width(candidate, 36) > max_width and _width(w, 36) < max_width):
            lines.append(line)
            line = w
        else:
            line = candidate
    if line != "":
        lines.append(line)
    return lines


func _width(s: String, size: int) -> float:
    return font.get_string_size(s, HORIZONTAL_ALIGNMENT_LEFT, -1, size).x
