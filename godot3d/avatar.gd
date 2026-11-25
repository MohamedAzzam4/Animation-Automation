class_name VRMAvatar
extends Node3D
## Loads AvatarSample_B (VRM 0.x via godot-vrm/MToon) and exposes deterministic
## control over blend shapes (expressions, visemes, blinks) and gaze bones.
##
## Conventions:
## - The avatar faces +Z at yaw 0. The VRM model node is rotated if needed.
## - All shape weights are set explicitly every frame (no hidden state), so the
##   render is a pure function of the schedule + frame number.

var skeleton: Skeleton3D
var face_meshes: Array = []            # meshes that own blend shapes
var shape_index: Dictionary = {}       # "Joy" -> [[mesh, idx], ...]
var model_root: Node3D                 # node that carries the 180 deg fix (if any)

const PREFIX := "Face.M_F00_000_00_Fcl_"

# semantic shape -> VRoid blend shape name suffix
const SHAPE_NAMES := {
        "Joy": "ALL_Joy", "Angry": "ALL_Angry", "Sorrow": "ALL_Sorrow",
        "Surprised": "ALL_Surprised", "Fun": "ALL_Fun", "Neutral": "ALL_Neutral",
        "Blink": "EYE_Close", "Blink_L": "EYE_Close_L", "Blink_R": "EYE_Close_R",
        "EyeSpread": "EYE_Spread",
        "MouthA": "MTH_A", "MouthI": "MTH_I", "MouthU": "MTH_U",
        "MouthE": "MTH_E", "MouthO": "MTH_O",
        "MouthUp": "MTH_Up", "MouthDown": "MTH_Down",
        "MouthAngry": "MTH_Angry", "MouthFun": "MTH_Fun", "MouthJoy": "MTH_Joy",
        "MouthSorrow": "MTH_Sorrow", "MouthSurprised": "MTH_Surprised",
}

# Preset composites used by the capability catalog (documented approximations).
# weight * intensity per shape. VRM0 override order is respected: mouth shapes
# of visemes are applied on top (additively, clamped) by the FaceDriver.
const EXPRESSION_PRESETS := {
        "neutral":   {},
        "happy":     {"Joy": 1.0},
        "smile":     {"Joy": 1.0},
        "sad":       {"Sorrow": 1.0},
        "surprised": {"Surprised": 1.0},
        "angry":     {"Angry": 1.0},
        "relaxed":   {"Fun": 1.0},
        "laugh":     {"Joy": 1.0, "MouthA": 0.45},
        "worried":   {"Sorrow": 0.7, "MouthSorrow": 0.5},
        "confused":  {"Surprised": 0.5, "MouthDown": 0.3},
        "thinking":  {"Joy": 0.15, "Blink_L": 0.35, "MouthUp": 0.2},
}

var _base_pose: Array = []             # per-bone rest pose snapshot (identity = retarget writes everything)

func _ready() -> void:
        var ps: PackedScene = load("res://assets3d/AvatarSample_B.vrm")
        var inst := ps.instantiate()
        add_child(inst)
        model_root = inst
        skeleton = _find(inst, "Skeleton3D") as Skeleton3D
        assert(skeleton != null, "VRMAvatar: no Skeleton3D in VRM scene")
        _collect_face_meshes(inst)
        _build_shape_index()
        _base_pose.resize(skeleton.get_bone_count())

static func _find(node: Node, type: String) -> Node:
        if node.is_class(type):
                return node
        for c in node.get_children():
                var r := _find(c, type)
                if r != null:
                        return r
        return null

func _collect_face_meshes(root: Node) -> void:
        _find_all(root, "MeshInstance3D", face_meshes)

static func _find_all(node: Node, type: String, out: Array) -> void:
        if node.is_class(type):
                out.append(node)
        for c in node.get_children():
                _find_all(c, type, out)

func _build_shape_index() -> void:
        shape_index.clear()
        for sem in SHAPE_NAMES:
                var suffix: String = SHAPE_NAMES[sem]
                var full := PREFIX + suffix
                for mi in face_meshes:
                        var mesh: Mesh = mi.mesh
                        if mesh == null:
                                continue
                        for i in mesh.get_blend_shape_count():
                                if mesh.get_blend_shape_name(i) == full:
                                        if not shape_index.has(sem):
                                                shape_index[sem] = []
                                        shape_index[sem].append([mi, i])

func has_shape(sem: String) -> bool:
        return shape_index.has(sem)

func set_shape(sem: String, weight: float) -> void:
        if not shape_index.has(sem):
                return
        var w := clampf(weight, 0.0, 1.0)
        for pair in shape_index[sem]:
                pair[0].set_blend_shape_value(pair[1], w)

func apply_expression(name: String, intensity: float) -> void:
        # reset all semantic shapes then set the composite
        for sem in SHAPE_NAMES:
                set_shape(sem, 0.0)
        var preset: Dictionary = EXPRESSION_PRESETS.get(name, {})
        for sem in preset:
                set_shape(String(sem), float(preset[sem]) * intensity)

func add_viseme(shape: String, weight: float) -> void:
        # viseme shapes stack ON TOP of the expression (VRM0: mouth overrides blend)
        var map := {"a": "MouthA", "e": "MouthE", "i": "MouthI", "o": "MouthO", "u": "MouthU"}
        var sem: String = map.get(shape, "")
        if sem == "":
                return
        for pair in shape_index.get(sem, []):
                var cur: float = pair[0].get_blend_shape_value(pair[1])
                pair[0].set_blend_shape_value(pair[1], clampf(cur + weight, 0.0, 1.0))

func add_blink(weight: float) -> void:
        for sem in ["Blink"]:
                for pair in shape_index.get(sem, []):
                        var cur: float = pair[0].get_blend_shape_value(pair[1])
                        pair[0].set_blend_shape_value(pair[1], clampf(cur + weight, 0.0, 1.0))

func bone_idx(name: String) -> int:
        return skeleton.find_bone(name)

func head_height() -> float:
        var hi := skeleton.find_bone("Head")
        if hi < 0:
                return 1.3
        return (skeleton.get_bone_global_rest(hi) * skeleton.global_transform).origin.y

func face_position() -> Vector3:
        # approximate head position for camera framing
        var hi := skeleton.find_bone("Head")
        if hi < 0:
                return global_position + Vector3.UP * 1.3
        var t: Transform3D = skeleton.global_transform * skeleton.get_bone_global_rest(hi)
        return t.origin
