class_name FaceDriver
extends Node
## Deterministic facial animation: expression crossfades, visemes, blinks,
## gaze (eyes+head+neck) and head nods, all driven by absolute frame numbers.
## apply() must be called AFTER BodyDriver.tick() so gaze offsets land on top
## of the animated body pose.

var avatar: VRMAvatar
var fps := 30.0
var frame := 0

# expression crossfade state
var _cur: Dictionary = {}        # semantic -> weight (currently displayed)
var _tgt: Dictionary = {}        # semantic -> weight (target composite)
var _fade_left := 0
var _fade_len := 9

# gaze smoothing
var _gaze_yaw := 0.0
var _gaze_pitch := 0.0

# schedule refs (may be empty)
var expressions: Array = []
var visemes: Array = []
var blinks: Array = []
var gaze: Array = []
var nods: Array = []

const EYE_YAW := 0.26
const EYE_PITCH := 0.16
const HEAD_YAW := 0.62
const HEAD_PITCH := 0.38
const NECK_YAW := 0.34
const NECK_PITCH := 0.20

func setup(av: VRMAvatar) -> void:
        avatar = av
        _cur = {}
        _tgt = {}

func load_schedule(sched: Dictionary) -> void:
        expressions = sched.get("expressions", [])
        visemes = sched.get("visemes", [])
        blinks = sched.get("blinks", [])
        gaze = sched.get("gaze", [])
        nods = sched.get("head_nod", [])
        frame = 0
        _cur = {}
        _tgt = {}
        _fade_left = 0

## Set expression target with crossfade (default 0.3 s).
func set_expression(name: String, intensity: float, fade_s: float = 0.3) -> void:
        var preset: Dictionary = avatar.EXPRESSION_PRESETS.get(name, {})
        var next: Dictionary = {}
        for sem in preset:
                next[sem] = float(preset[sem]) * intensity
        _tgt = next
        _fade_len = maxi(1, int(fade_s * fps))
        _fade_left = _fade_len

func _advance_crossfade() -> void:
        if _fade_left <= 0:
                return
        _fade_left -= 1
        var u := 1.0 - float(_fade_left) / float(_fade_len)
        var next: Dictionary = {}
        for sem in _cur:
                next[sem] = float(_cur[sem]) * (1.0 - u)
        for sem in _tgt:
                var w: float = float(_tgt[sem]) * u
                next[sem] = maxf(w, float(next.get(sem, 0.0)))
        _cur = next
        if _fade_left == 0:
                _cur = _tgt.duplicate()

func apply_frame() -> void:
        frame += 1
        _apply_expression_schedule()
        _advance_crossfade()
        # 1) base expression
        for sem in avatar.SHAPE_NAMES:
                avatar.set_shape(String(sem), 0.0)
        for sem in _cur:
                avatar.set_shape(String(sem), float(_cur[sem]))
        # 2) visemes (additive on the mouth)
        for v in visemes:
                var sf: int = int(v.get("start_frame", 0))
                var ef: int = int(v.get("end_frame", 0))
                if sf <= frame - 1 and frame - 1 < ef:
                        var w: float = float(v.get("weight", 0.5))
                        var ramp_in: float = clampf(float(frame - 1 - sf) / 2.0, 0.0, 1.0)
                        var ramp_out: float = clampf(float(ef - (frame - 1)) / 2.0, 0.0, 1.0)
                        avatar.add_viseme(String(v.get("shape", "a")), w * minf(ramp_in, ramp_out))
                        break
        # 3) blinks (impulse: 2 frames close, 5 open)
        for b in blinks:
                var bf: int = int(b.get("frame", -1))
                var d := (frame - 1) - bf
                if d >= 0 and d <= 7:
                        var w := 0.0
                        if d <= 1:
                                w = float(d + 1) / 2.0
                        else:
                                w = 1.0 - float(d - 1) / 6.0
                        avatar.add_blink(clampf(w, 0.0, 1.0))
                        break
        # 4) gaze + nod offsets on the skeleton
        _apply_gaze()
        _apply_nod()

func _active_seg(segs: Array) -> Dictionary:
        var best: Dictionary = {}
        for s in segs:
                if int(s.get("start_frame", 0)) <= frame - 1 and frame - 1 < int(s.get("end_frame", 0)):
                        best = s   # later segments win
        return best

func _apply_gaze() -> void:
        var seg := _active_seg(gaze)
        var tgt: Variant = null
        if not seg.is_empty():
                tgt = seg.get("target")
        var skel := avatar.skeleton
        var head_i := skel.find_bone("Head")
        if head_i < 0:
                return
        var head_tf: Transform3D = skel.get_bone_global_pose(head_i)
        var head_pos: Vector3 = (skel.global_transform * head_tf).origin
        if tgt != null:
                var dir: Vector3
                if tgt is Array and (tgt as Array).size() == 1 and String(tgt[0]) == "camera":
                        var cam := get_viewport().get_camera_3d()
                        if cam != null:
                                dir = cam.global_position - head_pos
                        else:
                                dir = Vector3.FORWARD
                else:
                        var t: Array = tgt
                        dir = Vector3(float(t[0]), float(t[1]), float(t[2])) - head_pos
                dir = avatar.global_transform.basis.inverse() * dir.normalized()
                var yaw := atan2(dir.x, dir.z)
                var pitch: float = asin(clampf(dir.y, -1.0, 1.0))
                _gaze_yaw = lerp_angle(_gaze_yaw, yaw, 0.25)
                _gaze_pitch = lerp_angle(_gaze_pitch, pitch, 0.25)
        else:
                _gaze_yaw = lerp_angle(_gaze_yaw, 0.0, 0.15)
                _gaze_pitch = lerp_angle(_gaze_pitch, 0.0, 0.15)
        # distribute
        var eye_yaw := clampf(_gaze_yaw, -EYE_YAW, EYE_YAW)
        var eye_pitch := clampf(_gaze_pitch, -EYE_PITCH, EYE_PITCH)
        var rem_yaw := _gaze_yaw - eye_yaw
        var rem_pitch := _gaze_pitch - eye_pitch
        var head_yaw := clampf(rem_yaw * 0.62, -HEAD_YAW, HEAD_YAW)
        var head_pitch := clampf(rem_pitch * 0.62, -HEAD_PITCH, HEAD_PITCH)
        var neck_yaw := clampf((rem_yaw - head_yaw) * 0.9, -NECK_YAW, NECK_YAW)
        var neck_pitch := clampf((rem_pitch - head_pitch) * 0.9, -NECK_PITCH, NECK_PITCH)
        # eyes (in head space)
        var q_eye := Quaternion(Vector3.UP, eye_yaw) * Quaternion(Vector3.RIGHT, -eye_pitch)
        for bone in ["LeftEye", "RightEye"]:
                var i := skel.find_bone(bone)
                if i >= 0:
                        skel.set_bone_pose_rotation(i, q_eye * (skel.get_bone_rest(i).basis.get_rotation_quaternion()))
        # head / neck offsets premultiplied (model-space)
        var q_head := Quaternion(Vector3.UP, head_yaw + _nod_yaw()) * Quaternion(Vector3.RIGHT, -(head_pitch + _nod_pitch()))
        var q_neck := Quaternion(Vector3.UP, neck_yaw) * Quaternion(Vector3.RIGHT, -neck_pitch)
        var hi := skel.find_bone("Head")
        var ni := skel.find_bone("Neck")
        if hi >= 0:
                skel.set_bone_pose_rotation(hi, q_head * skel.get_bone_pose_rotation(hi))
        if ni >= 0:
                skel.set_bone_pose_rotation(ni, q_neck * skel.get_bone_pose_rotation(ni))

var _nod_a := 0.0
var _nod_hz := 2.0

func _apply_nod() -> void:
        _nod_a = 0.0
        var seg := _active_seg(nods)
        if not seg.is_empty():
                var sf: int = int(seg.get("start_frame", 0))
                var ef: int = int(seg.get("end_frame", 0))
                _nod_a = float(seg.get("amplitude", 0.15))
                _nod_hz = float(seg.get("hz", 2.0))
                var t := float(frame - 1 - sf) / fps
                var dur := float(ef - sf) / fps
                var ramp := smoothstep(0.0, 0.25, t) * smoothstep(dur, dur - 0.25, t)
                _nod_a *= ramp
                _nod_phase = t * _nod_hz * TAU
        else:
                _nod_phase = 0.0

var _nod_phase := 0.0
var _last_expr: Dictionary = {}

func _apply_expression_schedule() -> void:
        var eseg := _active_seg(expressions)
        if eseg.is_empty():
                return
        if eseg.get("name") != _last_expr.get("name") or eseg.get("intensity") != _last_expr.get("intensity"):
                set_expression(String(eseg.get("name", "neutral")), float(eseg.get("intensity", 1.0)))
                _last_expr = eseg

func _nod_yaw() -> float:
        return 0.0

func _nod_pitch() -> float:
        if _nod_a <= 0.0:
                return 0.0
        return sin(_nod_phase) * _nod_a
