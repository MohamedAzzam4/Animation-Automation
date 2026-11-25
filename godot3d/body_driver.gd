class_name BodyDriver
extends Node
## Owns the retarget rigs and plays named body clips on the avatar with
## deterministic crossfades. Clips are retargeted UAL animations or procedural
## poses (head/spine offsets + 2-bone arm IK over the current stance base).

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
var _proc := ProcPoses.new()

var clip := "UAL1_Idle"
var clip_t0 := 0.0
var prev_clip := ""
var prev_clip_t0 := 0.0
var blend_frames := 12
var blend_start := -100000
var fps := 30.0
var frame := 0
var _last_retarg_clip := "UAL1_Idle"

func setup(av: VRMAvatar) -> void:
	avatar = av
	rig_ual1 = RetargetRig.new()
	rig_ual1.setup("res://assets3d/UAL1.glb", RetargetRig.UAL1_MAP, av.skeleton)
	add_child(rig_ual1)
	rig_ual2 = RetargetRig.new()
	rig_ual2.setup("res://assets3d/UAL2.glb", RetargetRig.UAL2_MAP, av.skeleton)
	add_child(rig_ual2)
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
	var src_cur: Dictionary = CLIP_SOURCES.get(clip, {})
	if String(src_cur.get("rig", "")) == "proc":
		_proc.post_ik(avatar.skeleton, String(src_cur.get("anim", "")), t - clip_t0)

func _sample_clip(name: String, phase: float) -> Dictionary:
	var src: Dictionary = CLIP_SOURCES.get(name, CLIP_SOURCES["UAL1_Idle"])
	if String(src["rig"]) == "proc":
		var base_src: Dictionary = CLIP_SOURCES.get(_last_retarg_clip, CLIP_SOURCES["UAL1_Idle"])
		var base := _rig(String(base_src["rig"])).sample(String(base_src["anim"]), phase)
		return _proc.apply(String(src["anim"]), phase, base, avatar.skeleton)
	_last_retarg_clip = name
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


class ProcPoses:
	## Procedural pose layer. Head/spine offsets go into the base pose dict;
	## arms are solved by 2-bone IK AFTER the base is applied (post_ik).

	func q_axis(axis: Vector3, ang: float) -> Quaternion:
		return Quaternion(axis.normalized(), ang)

	func ease_hold(u: float, ramp: float) -> float:
		# 0 -> 1 over [0, ramp] (u normalized 0..1 over the clip), then HOLD.
		# Clip crossfades own the exit blend.
		return smoothstep(0.0, 1.0, clampf(u / maxf(0.0001, ramp), 0.0, 1.0))

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
		var amp := ease_hold(phase / 4.0, 0.22)
		add_offset(base, skel, "Head", q_axis(Vector3(0, 0, 1), -0.08 * amp))

	func _apply_think(base: Dictionary, skel: Skeleton3D, phase: float) -> void:
		var amp := ease_hold(phase / 3.0, 0.3)
		add_offset(base, skel, "Head", q_axis(Vector3(0, 1, 0), -0.3 * amp) * q_axis(Vector3(1, 0, 0), -0.12 * amp) * q_axis(Vector3(0, 0, 1), 0.1 * amp))
		add_offset(base, skel, "UpperChest", q_axis(Vector3(0, 1, 0), -0.1 * amp))

	func _apply_hold_book(base: Dictionary, skel: Skeleton3D, phase: float) -> void:
		var amp := ease_hold(phase / 2.2, 0.28)
		add_offset(base, skel, "Head", q_axis(Vector3(1, 0, 0), 0.28 * amp))

	func _apply_turn(base: Dictionary, skel: Skeleton3D, phase: float, dir_sgn: float) -> void:
		var amp := ease_hold(phase / 1.0, 0.3)
		add_offset(base, skel, "UpperChest", q_axis(Vector3(0, 1, 0), dir_sgn * 0.35 * amp))
		add_offset(base, skel, "Head", q_axis(Vector3(0, 1, 0), dir_sgn * 0.3 * amp))
		add_offset(base, skel, "LeftUpperArm", q_axis(Vector3(0, 1, 0), dir_sgn * 0.1 * amp))
		add_offset(base, skel, "RightUpperArm", q_axis(Vector3(0, 1, 0), dir_sgn * 0.1 * amp))

	## ---------------- 2-bone arm IK (base-agnostic, manual FK) ---------------- ##

	func post_ik(skel: Skeleton3D, pose_name: String, phase: float) -> void:
		var cache: Dictionary = {}
		var head_pos: Vector3 = _live_global(skel, skel.find_bone("Head"), cache).origin
		match pose_name:
			"think":
				var tgt := head_pos + Vector3(-0.02, -0.12, 0.14)
				var u := ease_hold(phase / 3.0, 0.3)
				_relax_fingers(skel, "Right")
				_arm_ik(skel, "Right", _bind_hand(skel, "Right").lerp(tgt, u), Vector3(-0.5, -1, -0.35), cache)
			"point_right":
				var u2 := ease_hold(phase / 1.8, 0.25)
				var tgt2 := Vector3(-0.20, 0.90, 0.52)
				_arm_ik(skel, "Right", _bind_hand(skel, "Right").lerp(tgt2, u2), Vector3(-0.6, -1, -0.2), cache)
			"hold_book":
				var u3 := ease_hold(phase / 2.2, 0.28)
				var c := head_pos + Vector3(0.0, -0.20, 0.30)
				_relax_fingers(skel, "Left")
				_relax_fingers(skel, "Right")
				_arm_ik(skel, "Left", _bind_hand(skel, "Left").lerp(c + Vector3(0.12, 0, 0), u3), Vector3(0.5, -1, -0.3), cache)
				_arm_ik(skel, "Right", _bind_hand(skel, "Right").lerp(c + Vector3(-0.12, 0, 0), u3), Vector3(-0.5, -1, -0.3), cache)
			"wave":
				var u4 := ease_hold(phase / 4.0, 0.22)
				_relax_fingers(skel, "Right")
				var base_t := head_pos + Vector3(-0.30, -0.06, 0.12)
				var wag := sin(phase * TAU * 1.4) * 0.06
				var tgt3 := _bind_hand(skel, "Right").lerp(base_t + Vector3(wag, 0, 0), u4)
				_arm_ik(skel, "Right", tgt3, Vector3(-0.9, -0.6, -0.3), cache)

	func _live_global(skel: Skeleton3D, bone_i: int, cache: Dictionary) -> Transform3D:
		if bone_i < 0:
			return Transform3D.IDENTITY
		if cache.has(bone_i):
			return cache[bone_i]
		var lt := Transform3D(Basis(skel.get_bone_pose_rotation(bone_i)), skel.get_bone_pose_position(bone_i))
		var p: int = skel.get_bone_parent(bone_i)
		var gt := lt if p < 0 else _live_global(skel, p, cache) * lt
		cache[bone_i] = gt
		return gt

	func _relax_fingers(skel: Skeleton3D, side: String) -> void:
		for f in ["ThumbMetacarpal", "ThumbProximal", "ThumbDistal",
				"IndexProximal", "IndexIntermediate", "IndexDistal",
				"MiddleProximal", "MiddleIntermediate", "MiddleDistal",
				"RingProximal", "RingIntermediate", "RingDistal",
				"LittleProximal", "LittleIntermediate", "LittleDistal"]:
			var i := skel.find_bone(side + f)
			if i >= 0:
				skel.set_bone_pose_rotation(i, skel.get_bone_rest(i).basis.get_rotation_quaternion())

	func _bind_hand(skel: Skeleton3D, side: String) -> Vector3:
		var i := skel.find_bone(side + "Hand")
		if i < 0:
			return Vector3(0.3, 1.0, 0)
		return skel.get_bone_global_rest(i).origin

	func _arm_ik(skel: Skeleton3D, side: String, target: Vector3, pole: Vector3, cache: Dictionary) -> void:
		var up_i := skel.find_bone(side + "UpperArm")
		var lo_i := skel.find_bone(side + "LowerArm")
		var sh_i := skel.find_bone(side + "Shoulder")
		var hand_i := skel.find_bone(side + "Hand")
		if up_i < 0 or lo_i < 0 or hand_i < 0:
			return
		var up_pos: Vector3 = _live_global(skel, up_i, cache).origin
		var bind_up: Vector3 = skel.get_bone_global_rest(up_i).origin
		var bind_lo: Vector3 = skel.get_bone_global_rest(lo_i).origin
		var bind_hand: Vector3 = skel.get_bone_global_rest(hand_i).origin
		var a := bind_up.distance_to(bind_lo)
		var bl := bind_lo.distance_to(bind_hand)
		var d := clampf(up_pos.distance_to(target), absf(bl - a) + 0.015, a + bl - 0.015)
		var dir := (target - up_pos).normalized()
		var cos_a := clampf((a * a + d * d - bl * bl) / (2.0 * a * d), -1.0, 1.0)
		var ang := acos(cos_a)
		var bend := dir.cross(pole.normalized())
		if bend.length() < 0.001:
			bend = Vector3.UP
		bend = bend.normalized()
		var upper_dir := (dir.rotated(bend, ang)).normalized()
		var hand_pos := up_pos + dir * d
		var elbow := up_pos + upper_dir * a
		var fore_dir := (hand_pos - elbow).normalized()
		var q_sh: Quaternion = _live_global(skel, sh_i, cache).basis.get_rotation_quaternion() if sh_i >= 0 else Quaternion.IDENTITY
		var q_up := _dir_quat(skel, up_i, upper_dir)
		var q_lo := _dir_quat(skel, lo_i, fore_dir)
		skel.set_bone_pose_rotation(up_i, q_sh.inverse() * q_up)
		skel.set_bone_pose_rotation(lo_i, q_up.inverse() * q_lo)

	func _dir_quat(skel: Skeleton3D, bone_i: int, want_dir: Vector3) -> Quaternion:
		var kids := skel.get_bone_children(bone_i)
		if kids.size() == 0:
			return Quaternion.IDENTITY
		var child_i: int = kids[0]
		var bind_dir := (skel.get_bone_global_rest(child_i).origin - skel.get_bone_global_rest(bone_i).origin)
		if bind_dir.length() < 0.001:
			return Quaternion.IDENTITY
		bind_dir = bind_dir.normalized()
		var q := Quaternion(bind_dir, want_dir.normalized())
		return q * (skel.get_bone_global_rest(bone_i).basis.get_rotation_quaternion())
