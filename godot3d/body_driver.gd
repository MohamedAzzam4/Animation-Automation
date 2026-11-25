class_name BodyDriver
extends Node
## Owns the retarget rigs and plays named body clips on the avatar with
## deterministic crossfades. Clips are either retargeted UAL animations or
## procedural upper-body poses layered over the retargeted Idle base.

const CLIP_SOURCES := {
	"UAL1_Idle": {"rig": "ual1", "anim": "Idle"},
	"UAL1_Walk": {"rig": "ual1", "anim": "Walk"},
	"UAL1_Sitting_Enter": {"rig": "ual1", "anim": "Sitting_Enter"},
	"UAL1_Sitting_Idle": {"rig": "ual1", "anim": "Sitting_Idle"},
	"UAL1_Sitting_Exit": {"rig": "ual1", "anim": "Sitting_Exit"},
	"UAL1_Idle_Talking": {"rig": "ual1", "anim": "Idle_Talking"},
	"UAL1_Sitting_Talking": {"rig": "ual1", "anim": "Sitting_Talking"},
	"UAL2_Yes": {"rig": "ual2", "anim": "Yes"},
	"UAL2_Idle_No": {"rig": "ual2", "anim": "Idle_No"},
	"UAL2_Idle_FoldArms": {"rig": "ual2", "anim": "Idle_FoldArms"},
	"proc_wave": {"rig": "proc", "anim": "wave", "dur": 4.0},
	"proc_point_right": {"rig": "proc", "anim": "point_right", "dur": 1.8},
	"proc_think": {"rig": "proc", "anim": "think", "dur": 3.0},
	"proc_hold_book": {"rig": "proc", "anim": "hold_book", "dur": 2.2},
	"proc_turn_left": {"rig": "proc", "anim": "turn_left", "dur": 1.0},
	"proc_turn_right": {"rig": "proc", "anim": "turn_right", "dur": 1.0},
}

var avatar: VRMAvatar
var rig_ual1: RetargetRig
var rig_ual2: RetargetRig
var _proc: ProcPoses

var clip := "UAL1_Idle"
var clip_t0 := 0.0          # phase start time of current clip
var prev_clip := ""
var prev_clip_t0 := 0.0
var blend_frames := 12      # crossfade length in frames
var blend_start := -100000  # frame index when the current clip began

var fps := 30.0
var frame := 0

func setup(av: VRMAvatar) -> void:
	avatar = av
	rig_ual1 = RetargetRig.new()
	rig_ual1.setup("res://assets3d/UAL1.glb", RetargetRig.UAL1_MAP, av.skeleton)
	add_child(rig_ual1)
	rig_ual2 = RetargetRig.new()
	rig_ual2.setup("res://assets3d/UAL2.glb", RetargetRig.UAL2_MAP, av.skeleton)
	add_child(rig_ual2)
	_proc = ProcPoses.new()
	# reset unmapped bones to rest (hair/skirt/eyes follow their parents)
	var skel := avatar.skeleton
	for i in skel.get_bone_count():
		var rest := skel.get_bone_rest(i)
		skel.set_bone_pose_position(i, rest.origin)
		skel.set_bone_pose_rotation(i, rest.basis.get_rotation_quaternion())

func clip_length(name: String) -> float:
	var src: Dictionary = CLIP_SOURCES.get(name, {})
	if src.is_empty():
		return 0.0
	if String(src["rig"]) == "proc":
		return float(src["dur"])
	return _rig(String(src["rig"])).anim_length(String(src["anim"]))

func _rig(which: String) -> RetargetRig:
	return rig_ual1 if which == "ual1" else rig_ual2

## Switch clip with crossfade; call exactly once per frame BEFORE tick().
func set_clip(name: String, blend_f: int = 12) -> void:
	if name == clip:
		return
	assert(CLIP_SOURCES.has(name), "BodyDriver: unknown clip '%s'" % name)
	prev_clip = clip
	prev_clip_t0 = clip_t0
	clip = name
	clip_t0 = _now()
	blend_frames = maxi(1, blend_f)
	blend_start = frame

func _now() -> float:
	return frame / fps

## Advance one frame: sample, crossfade, apply to the avatar skeleton.
func tick(delta: float) -> void:
	frame += 1
	var t := _now()
	var pose_a := _sample_clip(clip, t - clip_t0)
	var alpha := 1.0
	if prev_clip != "" and (frame - blend_start) < blend_frames:
		alpha = smoothstep(0.0, 1.0, float(frame - blend_start) / float(blend_frames))
		var pose_b := _sample_clip(prev_clip, t - prev_clip_t0)
		pose_a = _mix(pose_b, pose_a, alpha)
	_apply(pose_a)

func _sample_clip(name: String, phase: float) -> Dictionary:
	var src: Dictionary = CLIP_SOURCES.get(name, CLIP_SOURCES["UAL1_Idle"])
	if String(src["rig"]) == "proc":
		var base := rig_ual1.sample("Idle", phase)
		return _proc.apply(String(src["anim"]), phase, base, avatar.skeleton)
	return _rig(String(src["rig"])).sample(String(src["anim"]), phase)

func _mix(a: Dictionary, b: Dictionary, alpha: float) -> Dictionary:
	var out: Dictionary = {}
	for k in b:
		if a.has(k):
			var pa: Dictionary = a[k]
			var pb: Dictionary = b[k]
			out[k] = {
				"q": (pa["q"] as Quaternion).slerp(pb["q"] as Quaternion, alpha),
				"p": (pa["p"] as Vector3).lerp(pb["p"] as Vector3, alpha),
			}
		else:
			out[k] = b[k]
	return out

func _apply(pose: Dictionary) -> void:
	var skel := avatar.skeleton
	for k in pose:
		var p: Dictionary = pose[k]
		skel.set_bone_pose_position(int(k), p["p"])
		skel.set_bone_pose_rotation(int(k), p["q"])


## ------------------------------------------------------------------ ##
## Procedural upper-body poses (parent-space premultiplied quaternions ##
## over the retargeted Idle base). All signed in MODEL space.          ##
## ------------------------------------------------------------------ ##
class ProcPoses:
	const LIMBS := {
		"RUA": "RightUpperArm", "RLA": "RightLowerArm", "RSH": "RightShoulder",
		"LUA": "LeftUpperArm", "LLA": "LeftLowerArm", "LSH": "LeftShoulder",
		"HEAD": "Head", "NECK": "Neck", "UCHEST": "UpperChest",
	}

	func q_axis(axis: Vector3, ang: float) -> Quaternion:
		return Quaternion(axis.normalized(), ang)

	func ease_hold(u: float, ramp: float) -> float:
		# 0 -> 1 over [0, ramp], hold, then 1 -> 0 over [1-ramp, 1]
		if u < ramp:
			return smoothstep(0.0, 1.0, u / ramp)
		if u > 1.0 - ramp:
			return smoothstep(0.0, 1.0, (1.0 - u) / ramp)
		return 1.0

	func add_offset(base: Dictionary, skel: Skeleton3D, bone: String, q: Quaternion) -> void:
		var i: int = skel.find_bone(bone)
		if i < 0 or not base.has(i):
			return
		var cur: Dictionary = base[i]
		cur["q"] = q * (cur["q"] as Quaternion)

	func apply(pose_name: String, phase: float, base: Dictionary, skel: Skeleton3D) -> Dictionary:
		match pose_name:
			"wave":
				_apply_wave(base, skel, phase)
			"point_right":
				_apply_point_right(base, skel, phase)
			"think":
				_apply_think(base, skel, phase)
			"hold_book":
				_apply_hold_book(base, skel, phase)
			"turn_left":
				_apply_turn(base, skel, phase, -1.0)
			"turn_right":
				_apply_turn(base, skel, phase, 1.0)
		return base

	func _apply_wave(base: Dictionary, skel: Skeleton3D, phase: float) -> void:
		var dur := 4.0
		var u := fmod(phase, dur) / dur
		if phase > dur:
			return
		var amp := ease_hold(u, 0.22)
		# raise the right arm ~50 deg up from T-pose (model-space Z rotation)
		add_offset(base, skel, "RightShoulder", q_axis(Vector3(0, 0, 1), -0.18 * amp))
		add_offset(base, skel, "RightUpperArm", q_axis(Vector3(0, 0, 1), 0.55 * amp) * q_axis(Vector3(0, 1, 0), -0.35 * amp))
		# wag the forearm around the raised arm axis
		var wag := sin(phase * PI * 2.0 * 1.4) * 0.45 * amp
		add_offset(base, skel, "RightLowerArm", q_axis(Vector3(0.6, 0.6, 0.5).normalized(), wag))
		add_offset(base, skel, "Head", q_axis(Vector3(0, 0, 1), -0.08 * amp))

	func _apply_point_right(base: Dictionary, skel: Skeleton3D, phase: float) -> void:
		var dur := 1.8
		if phase > dur:
			return
		var amp := ease_hold(phase / dur, 0.25)
		add_offset(base, skel, "RightShoulder", q_axis(Vector3(0, 0, 1), -0.1 * amp))
		add_offset(base, skel, "RightUpperArm", q_axis(Vector3(0, 1, 0), -1.35 * amp) * q_axis(Vector3(0, 0, 1), 0.12 * amp))
		add_offset(base, skel, "Head", q_axis(Vector3(0, 1, 0), 0.22 * amp))

	func _apply_think(base: Dictionary, skel: Skeleton3D, phase: float) -> void:
		var dur := 3.0
		if phase > dur:
			return
		var amp := ease_hold(phase / dur, 0.3)
		var sway := sin(phase * PI * 2.0 * 0.33) * 0.06
		add_offset(base, skel, "RightUpperArm", q_axis(Vector3(0, 0, 1), 0.95 * amp) * q_axis(Vector3(0, 1, 0), 0.55 * amp))
		add_offset(base, skel, "RightLowerArm", q_axis(Vector3(0, 0, 1), 1.75 * amp))
		add_offset(base, skel, "Head", q_axis(Vector3(0, 1, 0), -0.3 * amp) * q_axis(Vector3(1, 0, 0), -0.12 * amp) * q_axis(Vector3(0, 0, 1), 0.1 * amp))
		add_offset(base, skel, "UpperChest", q_axis(Vector3(0, 1, 0), -0.1 * amp + sway))

	func _apply_hold_book(base: Dictionary, skel: Skeleton3D, phase: float) -> void:
		var dur := 2.2
		if phase > dur:
			return
		var amp := ease_hold(phase / dur, 0.28)
		for side in [["Left", 1.0], ["Right", -1.0]]:
			var sgn: float = side[1]
			add_offset(base, skel, String(side[0]) + "UpperArm", q_axis(Vector3(0, 0, 1), 0.55 * amp * sgn))
			add_offset(base, skel, String(side[0]) + "LowerArm", q_axis(Vector3(0, 0, 1), 1.35 * amp * sgn) * q_axis(Vector3(0, 1, 0), 0.35 * amp * sgn))
		add_offset(base, skel, "Head", q_axis(Vector3(1, 0, 0), 0.28 * amp))

	func _apply_turn(base: Dictionary, skel: Skeleton3D, phase: float, dir_sgn: float) -> void:
		var dur := 1.0
		if phase > dur:
			return
		var amp := ease_hold(phase / dur, 0.3)
		add_offset(base, skel, "UpperChest", q_axis(Vector3(0, 1, 0), dir_sgn * 0.35 * amp))
		add_offset(base, skel, "Head", q_axis(Vector3(0, 1, 0), dir_sgn * 0.3 * amp))
		add_offset(base, skel, "LeftUpperArm", q_axis(Vector3(0, 1, 0), dir_sgn * 0.1 * amp))
		add_offset(base, skel, "RightUpperArm", q_axis(Vector3(0, 1, 0), dir_sgn * 0.1 * amp))
