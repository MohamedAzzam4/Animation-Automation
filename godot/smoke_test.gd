extends Node2D
var frames := 0
func _init() -> void:
	var tex := ImageTexture.create_from_image(Image.create(320, 240, false, Image.FORMAT_RGBA8))
func _process(_delta: float) -> void:
	queue_redraw()
	frames += 1
func _draw() -> void:
	draw_rect(Rect2(0, 0, 1280, 720), Color(0.15, 0.1, 0.2))
	draw_circle(Vector2(200 + frames * 4, 360), 120, Color(0.9, 0.6, 0.2))
	draw_string(ThemeDB.fallback_font, Vector2(40, 80), "Movie Maker OK %d" % frames, HORIZONTAL_ALIGNMENT_LEFT, -1, 32)
	if frames >= 30:
		get_tree().quit()
