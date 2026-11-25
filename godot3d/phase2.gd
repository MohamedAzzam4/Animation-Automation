extends Camera3D
## Phase 2: body animation reel — retargeted UAL clips, transitions,
## procedural poses, walk with real root translation, sit/stand at a chair.
## Everything is a pure function of the frame counter.

const FPS := 30

const BEATS := [
	{"clip": "UAL1_Idle", "dur": 4.0, "label": "UAL1_Idle (retargeted)", "cam": "wide"},
	{"clip": "UAL1_Walk", "dur": 4.0, "label": "UAL1_Walk + root translation (no foot-slide lock)", "cam": "side", "walk": true},
	{"clip": "UAL1_Idle", "dur": 2.0, "label": "transition: walk -> idle", "cam": "wide"},
	{"clip": "UAL1_Sitting_Enter", "dur": 2.6, "label": "UAL1_Sitting_Enter", "cam": "chair"},
	{"clip": "UAL1_Sitting_Idle", "dur": 2.5, "label": "UAL1_Sitting_Idle", "cam": "chair"},
	{"clip": "UAL1_Sitting_Talking", "dur": 3.0, "label": "UAL1_Sitting_Talking", "cam": "chair"},
	{"clip": "UAL1_Sitting_Exit", "dur": 2.5, "label": "UAL1_Sitting_Exit (stand up)", "cam": "chair"},
	{"clip": "UAL1_Idle_Talking", "dur": 3.0, "label": "UAL1_Idle_Talking", "cam": "chair"},
	{"clip": "UAL2_Yes", "dur": 2.5, "label": "UAL2_Yes (nod)", "cam": "chair"},
	{"clip": "UAL2_Idle_No", "dur": 2.5, "label": "UAL2_Idle_No (head shake)", "cam": "chair"},
	{"clip": "UAL2_Idle_FoldArms", "dur": 2.5, "label": "UAL2_Idle_FoldArms", "cam": "chair"},
	{"clip": "proc_wave", "dur": 4.0, "label": "proc_wave (procedural)", "cam": "chair"},
	{"clip": "proc_point_right", "dur": 1.8, "label": "proc_point_right (procedural)", "cam": "chair"},
	{"clip": "proc_think", "dur": 3.0, "label": "proc_think (procedural)", "cam": "chair"},
	{"clip": "proc_hold_book", "dur": 2.2, "label": "proc_hold_book (procedural)", "cam": "chair"},
	{"clip": "proc_turn_left", "dur": 1.0, "label": "proc_turn_left", "cam": "chair"},
	{"clip": "proc_turn_right", "dur": 1.0, "label": "proc_turn_right", "cam": "chair"},
	{"clip": "UAL1_Idle", "dur": 2.0, "label": "return to idle", "cam": "chair"},
]

const WALK_DEST := Vector3(0.0, 0.0, 2.2)

const CAM_OFFSETS := {
	"wide": {"off": Vector3(2.1, 1.32, 1.9), "tgt": Vector3(0, 1.02, 0.35), "fov": 45.0},
	"side": {"off": Vector3(2.75, 1.25, 0.9), "tgt": Vector3(0, 1.0, 1.3), "fov": 46.0},
	"chair": {"off": Vector3(2.05, 1.35, 1.05), "tgt": Vector3(0, 1.0, 0.55), "fov": 44.0},
}

var frame := 0
var avatar: VRMAvatar = null
var body: BodyDriver = null
var label: Label = null
var _beat_starts := []
var _total := 0
var _walk_origin := Vector3.ZERO

func _setup() -> void:
	if avatar != null:
		return
	avatar = get_node("../Avatar") as VRMAvatar
	body = get_node("../BodyDriver") as BodyDriver
	label = get_node("../UI/ViewLabel") as Label
	body.setup(avatar)
	_build_chair()
	var f := 0
	for b in BEATS:
		_beat_starts.append(f)
		f += int(float(b["dur"]) * FPS)
	_total = f + 15

func _build_chair() -> void:
	# simple deterministic chair facing +Z, seat centered at WALK_DEST
	var seat_y := 0.47
	var mat := StandardMaterial3D.new()
	mat.albedo_color = Color(0.55, 0.36, 0.22)
	var dark := StandardMaterial3D.new()
	dark.albedo_color = Color(0.32, 0.22, 0.15)
	var root := get_node("..") as Node3D
	var seat := MeshInstance3D.new()
	var box := BoxMesh.new()
	box.size = Vector3(0.46, 0.06, 0.46)
	box.material = mat
	seat.mesh = box
	seat.position = Vector3(WALK_DEST.x, seat_y, WALK_DEST.z)
	root.add_child(seat)
	var back := MeshInstance3D.new()
	var back_box := BoxMesh.new()
	back_box.size = Vector3(0.46, 0.55, 0.06)
	back_box.material = mat
	back.mesh = back_box
	back.position = Vector3(WALK_DEST.x, seat_y + 0.3, WALK_DEST.z - 0.23)
	root.add_child(back)
	for lx in [-0.18, 0.18]:
		for lz in [-0.18, 0.18]:
			var leg := MeshInstance3D.new()
			var lb := BoxMesh.new()
			lb.size = Vector3(0.05, seat_y, 0.05)
			lb.material = dark
			leg.mesh = lb
			leg.position = Vector3(WALK_DEST.x + lx, seat_y / 2.0, WALK_DEST.z + lz)
			root.add_child(leg)

func _process(_delta: float) -> void:
	_setup()
	var vi := clampi(frame / 1, 0, BEATS.size() - 1)
	var f_local := frame
	vi = 0
	for i in range(BEATS.size()):
		if frame >= _beat_starts[i]:
			vi = i
	f_local = frame - _beat_starts[vi]
	var beat: Dictionary = BEATS[vi]
	# clip switching (crossfade 0.4 s)
	if frame == _beat_starts[vi]:
		body.set_clip(String(beat["clip"]), 12)
	# walk path
	if beat.get("walk", false):
		var u: float = clampf(float(f_local) / (float(beat["dur"]) * FPS), 0.0, 1.0)
		avatar.global_position = _walk_origin.lerp(WALK_DEST, u)
	elif vi >= 2:
		avatar.global_position = WALK_DEST
	# camera (smooth blend across beats)
	var cam_now: Dictionary = CAM_OFFSETS[String(beat["cam"])]
	var tgt_pos: Vector3 = Vector3(cam_now["tgt"])
	var off: Vector3 = Vector3(cam_now["off"])
	var blend := 18
	if f_local < blend and vi > 0:
		var prev_beat: Dictionary = BEATS[vi - 1]
		var cam_prev: Dictionary = CAM_OFFSETS[String(prev_beat["cam"])]
		var uu := smoothstep(0.0, 1.0, float(f_local) / float(blend))
		off = (Vector3(cam_prev["off"])).lerp(off, uu)
		tgt_pos = (Vector3(cam_prev["tgt"])).lerp(tgt_pos, uu)
		fov = lerp(float(cam_prev["fov"]), float(cam_now["fov"]), uu)
	else:
		fov = float(cam_now["fov"])
	position = avatar.global_position + off
	look_at(avatar.global_position + tgt_pos, Vector3.UP)
	label.text = "PHASE 2  body animation (UAL -> VRM retarget)\n%d/18  %s" % [vi + 1, String(beat["label"])]
	body.tick(_delta)
	frame += 1
