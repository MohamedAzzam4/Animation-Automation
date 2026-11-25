class_name Director
extends Node3D
## Plays an interaction_v1 schedule on the avatar: paths, turns, body clips,
## facial layers, object attachments, door, camera, subtitles, fades and
## multi-scene switching. Pure function of the frame counter.
##
## Camera segment modes:
##   absolute        : pos/target are world coordinates (default)
##   avatar_relative : pos/target/push_to are OFFSETS from the avatar root
##                     (guarantees framing for a moving subject)

var avatar: VRMAvatar
var body: BodyDriver
var face: FaceDriver
var camera: Camera3D
var label: Label = null
var fade_rect: ColorRect = null
var env_root: Node3D = null
var env_name := "test_room"

var sched: Dictionary = {}
var frame := 0
var total_frames := 0
var fps := 30.0
var objects: Dictionary = {}
var attachments_done: Dictionary = {}
var door_hinge: Node3D = null
var cam_prev_pos := Vector3.ZERO
var cam_prev_valid := false
var _last_body_seg: Dictionary = {}
var _env_builder := EnvBuilder.new()

func setup(av: VRMAvatar, bd: BodyDriver, fd: FaceDriver, cam: Camera3D, ui_label: Label = null, rect: ColorRect = null) -> void:
        avatar = av
        body = bd
        face = fd
        camera = cam
        label = ui_label
        fade_rect = rect
        body.setup(avatar)
        face.setup(avatar)

func load_schedule(sched_path: String) -> void:
        var f := FileAccess.open(sched_path, FileAccess.READ)
        sched = JSON.parse_string(f.get_as_text())
        f.close()
        total_frames = int(sched.get("total_frames", 0))
        fps = float(sched.get("fps", 30.0))
        face.load_schedule(sched)
        env_name = String(sched.get("environment", "test_room"))
        _switch_env(env_name)
        for obj_name in sched.get("objects", {}):
                var o: Dictionary = sched["objects"][obj_name]
                spawn_object(String(obj_name), Vector3(float(o["pos"][0]), float(o["pos"][1]), float(o["pos"][2])))
        avatar.global_position = _path_start()
        avatar.rotation.y = deg_to_rad(_turn_start())

func _switch_env(env: String) -> void:
        if env_root != null:
                env_root.queue_free()
        env_root = _env_builder.build(env)
        add_child(env_root)
        env_name = env
        door_hinge = Director._find_node(env_root, "DoorHinge")
        for obj_name in objects:
                var node: Node3D = objects[obj_name]
                if node.get_parent() != env_root:
                        node.reparent(env_root)

func spawn_object(name_s: String, pos: Vector3) -> void:
        if objects.has(name_s):
                return
        var node: Node3D = null
        if name_s == "mug":
                node = _env_builder._cyl(env_root, 0.045, 0.1, pos + Vector3(0, 0.05, 0), Color(0.85, 0.3, 0.25), "Mug")
        elif name_s == "book":
                node = _env_builder._box(env_root, Vector3(0.17, 0.035, 0.23), pos + Vector3(0, 0.018, 0), Color(0.2, 0.35, 0.6), "Book")
        else:
                node = _env_builder._box(env_root, Vector3(0.1, 0.1, 0.1), pos, Color(0.7, 0.7, 0.7), name_s)
        objects[name_s] = node

func _path_start() -> Vector3:
        var paths: Array = sched.get("paths", [])
        if not paths.is_empty():
                var p0: Dictionary = paths[0]
                return Vector3(float(p0["from"][0]), float(p0["from"][1]), float(p0["from"][2]))
        return Vector3.ZERO

func _turn_start() -> float:
        var turns: Array = sched.get("turns", [])
        if not turns.is_empty():
                return float(turns[0]["from_yaw_deg"])
        return 0.0

static func _seg_at(segs: Array, f: int) -> Dictionary:
        var best: Dictionary = {}
        for s in segs:
                if int(s.get("start_frame", 0)) <= f and f < int(s.get("end_frame", 0)):
                        best = s
        return best

func tick(delta: float) -> void:
        var f := frame
        # --- scene switching (multi-env stories) ---
        for s in sched.get("scenes", []):
                if int(s.get("start_frame", 0)) <= f:
                        var want_env := String(s.get("environment", env_name))
                        if want_env != env_name:
                                _switch_env(want_env)
        # --- paths (position) ---
        var pseg := _seg_at(sched.get("paths", []), f)
        if not pseg.is_empty():
                var sf: int = int(pseg["start_frame"])
                var ef: int = int(pseg["end_frame"])
                var u: float = clampf(float(f - sf) / maxf(1.0, float(ef - sf)), 0.0, 1.0)
                var from := Vector3(float(pseg["from"][0]), float(pseg["from"][1]), float(pseg["from"][2]))
                var to := Vector3(float(pseg["to"][0]), float(pseg["to"][1]), float(pseg["to"][2]))
                avatar.global_position = from.lerp(to, u)
        # --- turns (yaw) ---
        var tseg := _seg_at(sched.get("turns", []), f)
        if not tseg.is_empty():
                var sf2: int = int(tseg["start_frame"])
                var ef2: int = int(tseg["end_frame"])
                var u2: float = clampf(float(f - sf2) / maxf(1.0, float(ef2 - sf2)), 0.0, 1.0)
                avatar.rotation.y = deg_to_rad(lerp_angle(deg_to_rad(float(tseg["from_yaw_deg"])), deg_to_rad(float(tseg["to_yaw_deg"])), u2))
        # --- body ---
        var bseg := _seg_at(sched.get("body", []), f)
        if not bseg.is_empty() and bseg != _last_body_seg:
                body.set_clip(String(bseg.get("clip", "UAL1_Idle")), int(float(bseg.get("blend", 0.4)) * fps))
                _last_body_seg = bseg
        body.tick(delta)
        # --- face ---
        face.apply_frame()
        # --- attachments (exact-frame events) ---
        for att in sched.get("attachments", []):
                var af: int = int(att.get("frame", -1))
                var obj_name := String(att.get("object", ""))
                if f == af and not attachments_done.has(obj_name + str(af)):
                        attachments_done[obj_name + str(af)] = true
                        _do_attachment(att)
        _update_attachment_tweens()
        # --- door ---
        for dseg in sched.get("door", {}).get("segments", []):
                var dsf: int = int(dseg.get("start_frame", 0))
                var def_: int = int(dseg.get("end_frame", 1))
                if dsf <= f and f < def_ and door_hinge != null:
                        var du: float = clampf(float(f - dsf) / maxf(1.0, float(def_ - dsf)), 0.0, 1.0)
                        door_hinge.rotation.y = deg_to_rad(float(dseg.get("to_deg", 0.0)) * smoothstep(0.0, 1.0, du))
        # --- camera ---
        _apply_camera(f)
        # --- subtitles / label ---
        if label != null:
                var lbl := ""
                var sseg := _seg_at(sched.get("subtitles", []), f)
                if not sseg.is_empty():
                        lbl = String(sseg.get("text", ""))
                label.text = lbl
        # --- fades ---
        if fade_rect != null:
                var alpha := 0.0
                for fseg in sched.get("fades", []):
                        var fsf: int = int(fseg.get("start_frame", 0))
                        var fef: int = int(fseg.get("end_frame", 1))
                        if fsf <= f and f < fef:
                                var half := float(fef - fsf) / 2.0
                                alpha = 1.0 - absf(float(f - fsf) - half) / half
                fade_rect.color.a = clampf(alpha, 0.0, 1.0)
        frame += 1
        if total_frames > 0 and frame >= total_frames:
                get_tree().quit()

func _do_attachment(att: Dictionary) -> void:
        var obj_name := String(att.get("object", ""))
        if not objects.has(obj_name):
                return
        var node: Node3D = objects[obj_name]
        if String(att.get("mode", "world")) == "hand":
                var bone_i := avatar.skeleton.find_bone(String(att.get("bone", "RightHand")))
                if bone_i < 0:
                        return
                var ba := BoneAttachment3D.new()
                ba.bone_idx = bone_i
                ba.name = "Hold_" + obj_name
                avatar.skeleton.add_child(ba)
                var offset := Vector3(float(att["offset"][0]), float(att["offset"][1]), float(att["offset"][2]))
                node.reparent(ba)
                node.position = offset + Vector3(0.10, 0.06, 0.0)  # slide-in start
                node.rotation = Vector3.ZERO
                attach_state[obj_name] = {"tween_start": frame, "tween_frames": int(att.get("tween_frames", 8)),
                        "from_local": offset + Vector3(0.10, 0.06, 0.0), "to_local": offset}
        else:
                var pos_v := Vector3(float(att["pos"][0]), float(att["pos"][1]), float(att["pos"][2]))
                var from_xform := node.global_transform
                node.reparent(env_root)
                attach_state[obj_name] = {"tween_start": frame, "tween_frames": int(att.get("tween_frames", 22)),
                        "from_world": from_xform, "to_pos": pos_v + (Vector3(0, 0.05, 0) if obj_name == "mug" else Vector3(0, 0.018, 0))}

var attach_state: Dictionary = {}

func _update_attachment_tweens() -> void:
        for obj_name in attach_state:
                var st: Dictionary = attach_state[obj_name]
                var t := float(frame - int(st["tween_start"])) / maxf(1.0, float(st["tween_frames"]))
                if t >= 1.0:
                        continue
                var node: Node3D = objects.get(obj_name)
                if node == null:
                        continue
                var s := smoothstep(0.0, 1.0, t)
                if st.has("from_local"):
                        node.position = (Vector3(st["from_local"])).lerp(Vector3(st["to_local"]), s)
                elif st.has("from_world"):
                        node.global_position = (Vector3(st["from_world"].origin)).lerp(Vector3(st["to_pos"]), s)

func _apply_camera(f: int) -> void:
        var cseg := _seg_at(sched.get("camera", []), f)
        if cseg.is_empty():
                if sched.get("camera", []).is_empty():
                        # default: character-relative 3/4 shot
                        camera.position = avatar.global_position + Vector3(1.9, 1.35, 1.55)
                        camera.look_at(avatar.global_position + Vector3(0, 1.0, 0), Vector3.UP)
                        camera.fov = 44.0
                        cam_prev_pos = camera.position
                        cam_prev_valid = true
                return
        var sf: int = int(cseg["start_frame"])
        var ef: int = int(cseg["end_frame"])
        var u: float = clampf(float(f - sf) / maxf(1.0, float(ef - sf)), 0.0, 1.0)
        var pos := Vector3(float(cseg["pos"][0]), float(cseg["pos"][1]), float(cseg["pos"][2]))
        var tgt := Vector3(float(cseg["target"][0]), float(cseg["target"][1]), float(cseg["target"][2]))
        if bool(cseg.get("avatar_relative", false)):
                var base := avatar.global_position
                pos = base + pos
                tgt = base + tgt
                if cseg.has("push_to"):
                        var push_r := Vector3(float(cseg["push_to"][0]), float(cseg["push_to"][1]), float(cseg["push_to"][2]))
                        pos = pos.lerp(base + push_r, smoothstep(0.0, 1.0, u))
        elif bool(cseg.get("yaw_relative", false)):
                # offsets authored in the +Z-facing frame, rotated by the avatar yaw
                var base2 := avatar.global_position
                var yaw := avatar.rotation.y
                pos = base2 + Vector3(cseg["pos"][0], cseg["pos"][1], cseg["pos"][2]).rotated(Vector3.UP, yaw)
                tgt = base2 + Vector3(cseg["target"][0], cseg["target"][1], cseg["target"][2]).rotated(Vector3.UP, yaw)
                if cseg.has("push_to"):
                        var push_y := Vector3(cseg["push_to"][0], cseg["push_to"][1], cseg["push_to"][2]).rotated(Vector3.UP, yaw)
                        pos = pos.lerp(base2 + push_y, smoothstep(0.0, 1.0, u))
        else:
                if cseg.has("push_to"):
                        var push := Vector3(float(cseg["push_to"][0]), float(cseg["push_to"][1]), float(cseg["push_to"][2]))
                        pos = pos.lerp(push, smoothstep(0.0, 1.0, u))
        # keep the camera inside the room (yaw-rotated offsets can hit walls);
        # walls are 0.06-thick boxes at the bounds, keep 0.25 m margin
        var bounds: Array = sched.get("camera_bounds", [])
        if bounds.size() == 4:
                pos.x = clampf(pos.x, float(bounds[0]), float(bounds[1]))
                pos.z = clampf(pos.z, float(bounds[2]), float(bounds[3]))
        if bool(cseg.get("smooth", false)) and cam_prev_valid:
                pos = cam_prev_pos.lerp(pos, 0.08)
        camera.position = pos
        camera.look_at(tgt, Vector3.UP)
        if cseg.has("fov"):
                camera.fov = float(cseg["fov"])
        cam_prev_pos = camera.position
        cam_prev_valid = true

static func _find_node(node: Node, name_s: String) -> Node:
        if node.name == name_s:
                return node
        for c in node.get_children():
                var r := _find_node(c, name_s)
                if r != null:
                        return r
        return null
