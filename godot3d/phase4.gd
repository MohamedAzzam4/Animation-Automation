extends Camera3D
## Phase 4: lip-sync A/B comparison scene.
## Renders one method from a schedule (--sched), logging per-frame mouth
## state to CSV (--log) and showing the method label (--label).

var frame := 0
var avatar: VRMAvatar = null
var body: BodyDriver = null
var face: FaceDriver = null
var label: Label = null
var total_frames := 920
var log_path := ""
var label_text := "lip-sync"
var _log: FileAccess

func _setup() -> void:
	if avatar != null:
		return
	avatar = get_node("../Avatar") as VRMAvatar
	body = get_node("../BodyDriver") as BodyDriver
	face = get_node("../FaceDriver") as FaceDriver
	label = get_node("../UI/ViewLabel") as Label
	body.setup(avatar)
	face.setup(avatar)
	for arg in OS.get_cmdline_user_args():
		var s := String(arg)
		if s.begins_with("--sched="):
			var f := FileAccess.open(s.substr(8), FileAccess.READ)
			var sched: Dictionary = JSON.parse_string(f.get_as_text())
			f.close()
			total_frames = int(sched.get("total_frames", 920))
			face.load_schedule(sched)
		elif s.begins_with("--log="):
			log_path = s.substr(6)
		elif s.begins_with("--label="):
			label_text = s.substr(8)
	if log_path != "":
		_log = FileAccess.open(log_path, FileAccess.WRITE)
		_log.store_line("frame,viseme_shape,viseme_weight,expression")

func _process(delta: float) -> void:
	_setup()
	var t := float(frame) / 30.0
	var a := 0.34 + 0.06 * sin(t * 0.17)
	position = avatar.global_position + Vector3(sin(a) * 1.05, 1.40, cos(a) * 1.05)
	look_at(avatar.face_position(), Vector3.UP)
	fov = 30.0
	label.text = "PHASE 4  lip-sync\n%s" % label_text
	body.tick(delta)
	face.apply_frame()
	if _log != null:
		var shape := "-"
		var weight := 0.0
		for v in face.visemes:
			if int(v.get("start_frame", 0)) <= frame and frame < int(v.get("end_frame", 0)):
				shape = String(v.get("shape", "-"))
				weight = float(v.get("weight", 0.0))
				break
		var expr_name := "neutral"
		for e in face.expressions:
			if int(e.get("start_frame", 0)) <= frame and frame < int(e.get("end_frame", 0)):
				expr_name = String(e.get("name", "neutral"))
		_log.store_line("%d,%s,%.3f,%s" % [frame, shape, weight, expr_name])
	frame += 1
	if frame >= total_frames + 5:
		if _log != null:
			_log.close()
		get_tree().quit()
