extends Camera3D
# Phase 0: deterministic slow orbit for the environment check.
# Under Movie Maker --fixed-fps 30 every delta is exactly 1/30, so the
# orbit angle is a pure function of the frame number.
var _a := 0.0

func _process(delta: float) -> void:
	_a += delta * 0.22
	var r := 5.6
	position = Vector3(sin(_a) * r, 2.5, cos(_a) * r)
	look_at(Vector3(0.0, 0.6, 0.0), Vector3.UP)
