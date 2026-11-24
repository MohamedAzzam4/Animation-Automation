extends Node2D
# Phase 1 acceptance test: every final asset must load, and the characters must
# composite into a recognizable two-shot with overlays applied.
# DESIGN RULE learned here: never call load() inside _draw(); preload textures in
# _ready() (re-entrant resource loading during the draw pass corrupts the canvas item).

var report := {"loaded": 0, "failed": []}
var tex_cache := {}

func _ready() -> void:
    var args := OS.get_cmdline_user_args()
    var out_dir := "/tmp" if args.size() < 2 else args[1]
    var dir := DirAccess.open("res://assets")
    var files := []
    _collect(dir, "res://assets", files)
    for path in files:
        var tex: Texture2D = load(path)
        if tex == null or tex.get_width() < 1:
            report.failed.append(path)
        else:
            report.loaded += 1
            tex_cache[path] = tex
    _settle_and_report(out_dir)
    queue_redraw()

func _collect(dir: DirAccess, base: String, out: Array) -> void:
    for name in dir.get_files():
        if name.ends_with(".png"):
            out.append(base + "/" + name)
    for name in dir.get_directories():
        var sub := DirAccess.open(base + "/" + name)
        if sub:
            _collect(sub, base + "/" + name, out)

func _process(_delta: float) -> void:
    queue_redraw()

func _settle_and_report(out_dir: String) -> void:
    for i in 10:
        await get_tree().process_frame
    var f := FileAccess.open(out_dir + "/test_assets_report.json", FileAccess.WRITE)
    f.store_string(JSON.stringify(report, "\t"))
    print("TEST_ASSETS loaded=", report.loaded, " failed=", report.failed.size())
    get_tree().quit(0 if report.failed.is_empty() else 1)

func _tex(path: String) -> Texture2D:
    return tex_cache.get(path)

func _draw() -> void:
    var bg: Texture2D = _tex("res://assets/backgrounds/student_room.png")
    draw_texture_rect(bg, Rect2(0, 0, 1280, 720), false)
    # Anna: mouth-erased base + open mouth overlay = speaking composite
    var anna_m: Texture2D = _tex("res://assets/characters/anna/expr_neutral_noMouth.png")
    var anna_mo: Texture2D = _tex("res://assets/characters/anna/expr_neutral_mouth2.png")
    draw_texture_rect(anna_m, Rect2(80, 160, 360, 480), false)
    draw_texture_rect(anna_mo, Rect2(80, 160, 360, 480), false)
    # Ben: base + blink overlay = blinking composite
    var ben: Texture2D = _tex("res://assets/characters/ben/expr_neutral.png")
    var ben_blink: Texture2D = _tex("res://assets/characters/ben/expr_neutral_blink.png")
    draw_texture_rect(ben, Rect2(840, 160, 360, 510), false)
    draw_texture_rect(ben_blink, Rect2(840, 160, 360, 510), false)
    draw_string(ThemeDB.fallback_font, Vector2(40, 60), "Phase 1 asset composite test",
        HORIZONTAL_ALIGNMENT_LEFT, -1, 28)
