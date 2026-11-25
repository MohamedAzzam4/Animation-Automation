extends Camera3D
## Phase 3: facial expression showcase driven by face_schedule.json.
## Segments: expressions at 4 intensities, composites, gaze work, nods, blinks.

var frame := 0
var avatar: VRMAvatar = null
var body: BodyDriver = null
var face: FaceDriver = null
var label: Label = null
var sched: Dictionary = {}
var total_frames := 1560
var _last_expr_seg: Dictionary = {}

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
		if String(arg).begins_with("--sched="):
			var path := String(arg).substr(8)
			var f := FileAccess.open(path, FileAccess.READ)
			sched = JSON.parse_string(f.get_as_text())
			f.close()
			total_frames = int(sched.get("total_frames", 1560))
			face.load_schedule(sched)
			print("phase3 schedule loaded: ", path, " frames=", total_frames)

func _process(delta: float) -> void:
	_setup()
	# camera: slow deterministic drift around the face
	var t := float(frame) / 30.0
	var a := 0.30 + 0.10 * sin(t * 0.21)
	position = avatar.global_position + Vector3(sin(a) * 0.98, 1.42, cos(a) * 0.98)
	look_at(avatar.face_position() + Vector3(0, 0.01, 0), Vector3.UP)
	fov = 26.0
	# label from the active expression segment
	var lbl := "PHASE 3  facial expressions (VRM blend shapes)"
	for s in sched.get("expressions", []):
		if int(s.get("start_frame", 0)) <= frame and frame < int(s.get("end_frame", 0)):
			lbl = "PHASE 3  facial expressions\n%s  (intensity %.2f)" % [String(s.get("label", s.get("name", "?"))), float(s.get("intensity", 0.0))]
	label.text = lbl
	body.tick(delta)
	face.apply_frame()
	frame += 1
	if frame >= total_frames + 20:
		get_tree().quit()
