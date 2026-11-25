class_name RetargetRig
extends Node
## Runtime world-delta retargeter: samples an animation from a Quaternius UAL
## GLB rig and solves equivalent LOCAL bone poses for the VRM avatar skeleton.
##
## Method (classic world-delta retarget):
##   For each mapped bone b (topological order, parents first):
##     Wa_src(b)  = Wa_src(parent) * Lsrc(b)          # animated world rot
##     D(b)       = Wa_src(b) * Wb_src(b)^-1          # world-space delta vs bind
##     Wa_dst(b)  = D(b) * Wb_dst(b)                  # apply delta to target bind
##     L_dst(b)   = Wa_dst(parent)^-1 * Wa_dst(b)     # back to local
##   Hips translation: bind + (anim - bind) * scale, XZ locked (paths own it).
##
## Deterministic: pure function of (clip, time). No physics, no RNG.

var src_root: Node3D
var src_skel: Skeleton3D
var player: AnimationPlayer

var map: Dictionary = {}          # avatar bone idx -> src bone idx
var order: Array = []             # avatar bone idx, parents first
var src_bind_q: Dictionary = {}   # src idx -> Quaternion (world bind)
var dst_bind_q: Dictionary = {}   # avatar idx -> Quaternion (world bind)
var dst_bind_pos: Dictionary = {} # avatar idx -> Vector3 (local bind)
var mapped_ancestor: Dictionary = {}   # avatar idx -> nearest mapped ancestor (-1 none)
var dst_parent_bind_q: Dictionary = {} # avatar idx -> Quaternion (when ancestor unmapped)
var src_parent_bind_q: Dictionary = {} # avatar idx -> Quaternion (src parent unmapped: root bone)
var src_hips_bind_pos := Vector3.ZERO
var dst_hips_bind_pos := Vector3.ZERO
var src_root_basis := Basis.IDENTITY     # src hips parent (root bone) world basis
var dst_root_basis_inv := Basis.IDENTITY # avatar hips parent world basis (inverted)
var scale := 1.0
var hips_i := -1

const UAL1_MAP := {
        "Hips": "DEF-hips", "Spine": "DEF-spine.001", "Chest": "DEF-spine.002",
        "UpperChest": "DEF-spine.003", "Neck": "DEF-neck", "Head": "DEF-head",
        "LeftShoulder": "DEF-shoulder.L", "RightShoulder": "DEF-shoulder.R",
        "LeftUpperArm": "DEF-upper_arm.L", "RightUpperArm": "DEF-upper_arm.R",
        "LeftLowerArm": "DEF-forearm.L", "RightLowerArm": "DEF-forearm.R",
        "LeftHand": "DEF-hand.L", "RightHand": "DEF-hand.R",
        "LeftUpperLeg": "DEF-thigh.L", "RightUpperLeg": "DEF-thigh.R",
        "LeftLowerLeg": "DEF-shin.L", "RightLowerLeg": "DEF-shin.R",
        "LeftFoot": "DEF-foot.L", "RightFoot": "DEF-foot.R",
        "LeftToes": "DEF-toe.L", "RightToes": "DEF-toe.R",
        "LeftThumbMetacarpal": "DEF-thumb.01.L", "LeftThumbProximal": "DEF-thumb.02.L",
        "LeftThumbDistal": "DEF-thumb.03.L",
        "RightThumbMetacarpal": "DEF-thumb.01.R", "RightThumbProximal": "DEF-thumb.02.R",
        "RightThumbDistal": "DEF-thumb.03.R",
        "LeftIndexProximal": "DEF-f_index.01.L", "LeftIndexIntermediate": "DEF-f_index.02.L",
        "LeftIndexDistal": "DEF-f_index.03.L",
        "RightIndexProximal": "DEF-f_index.01.R", "RightIndexIntermediate": "DEF-f_index.02.R",
        "RightIndexDistal": "DEF-f_index.03.R",
        "LeftMiddleProximal": "DEF-f_middle.01.L", "LeftMiddleIntermediate": "DEF-f_middle.02.L",
        "LeftMiddleDistal": "DEF-f_middle.03.L",
        "RightMiddleProximal": "DEF-f_middle.01.R", "RightMiddleIntermediate": "DEF-f_middle.02.R",
        "RightMiddleDistal": "DEF-f_middle.03.R",
        "LeftRingProximal": "DEF-f_ring.01.L", "LeftRingIntermediate": "DEF-f_ring.02.L",
        "LeftRingDistal": "DEF-f_ring.03.L",
        "RightRingProximal": "DEF-f_ring.01.R", "RightRingIntermediate": "DEF-f_ring.02.R",
        "RightRingDistal": "DEF-f_ring.03.R",
        "LeftLittleProximal": "DEF-f_pinky.01.L", "LeftLittleIntermediate": "DEF-f_pinky.02.L",
        "LeftLittleDistal": "DEF-f_pinky.03.L",
        "RightLittleProximal": "DEF-f_pinky.01.R", "RightLittleIntermediate": "DEF-f_pinky.02.R",
        "RightLittleDistal": "DEF-f_pinky.03.R",
}

const UAL2_MAP := {
        "Hips": "pelvis", "Spine": "spine_01", "Chest": "spine_02", "UpperChest": "spine_03",
        "Neck": "neck_01", "Head": "Head",
        "LeftShoulder": "clavicle_l", "RightShoulder": "clavicle_r",
        "LeftUpperArm": "upperarm_l", "RightUpperArm": "upperarm_r",
        "LeftLowerArm": "lowerarm_l", "RightLowerArm": "lowerarm_r",
        "LeftHand": "hand_l", "RightHand": "hand_r",
        "LeftUpperLeg": "thigh_l", "RightUpperLeg": "thigh_r",
        "LeftLowerLeg": "calf_l", "RightLowerLeg": "calf_r",
        "LeftFoot": "foot_l", "RightFoot": "foot_r",
        "LeftToes": "ball_l", "RightToes": "ball_r",
        "LeftThumbMetacarpal": "thumb_01_l", "LeftThumbProximal": "thumb_02_l",
        "LeftThumbDistal": "thumb_03_l",
        "RightThumbMetacarpal": "thumb_01_r", "RightThumbProximal": "thumb_02_r",
        "RightThumbDistal": "thumb_03_r",
        "LeftIndexProximal": "index_01_l", "LeftIndexIntermediate": "index_02_l",
        "LeftIndexDistal": "index_03_l",
        "RightIndexProximal": "index_01_r", "RightIndexIntermediate": "index_02_r",
        "RightIndexDistal": "index_03_r",
        "LeftMiddleProximal": "middle_01_l", "LeftMiddleIntermediate": "middle_02_l",
        "LeftMiddleDistal": "middle_03_l",
        "RightMiddleProximal": "middle_01_r", "RightMiddleIntermediate": "middle_02_r",
        "RightMiddleDistal": "middle_03_r",
        "LeftRingProximal": "ring_01_l", "LeftRingIntermediate": "ring_02_l",
        "LeftRingDistal": "ring_03_l",
        "RightRingProximal": "ring_01_r", "RightRingIntermediate": "ring_02_r",
        "RightRingDistal": "ring_03_r",
        "LeftLittleProximal": "pinky_01_l", "LeftLittleIntermediate": "pinky_02_l",
        "LeftLittleDistal": "pinky_03_l",
        "RightLittleProximal": "pinky_01_r", "RightLittleIntermediate": "pinky_02_r",
        "RightLittleDistal": "pinky_03_r",
}

func setup(glb_path: String, bone_map: Dictionary, avatar_skel: Skeleton3D) -> void:
        var ps: PackedScene = load(glb_path)
        src_root = ps.instantiate()
        add_child(src_root)
        src_root.visible = false
        src_skel = _find_type(src_root, "Skeleton3D") as Skeleton3D
        player = _find_type(src_root, "AnimationPlayer") as AnimationPlayer
        assert(src_skel != null and player != null, "RetargetRig: missing skeleton/player in " + glb_path)
        player.playback_process_mode = AnimationPlayer.ANIMATION_PROCESS_MANUAL

        for av_name in bone_map:
                var av_i: int = avatar_skel.find_bone(String(av_name))
                var src_i: int = src_skel.find_bone(String(bone_map[av_name]))
                if av_i < 0 or src_i < 0:
                        push_warning("retarget: bone pair missing %s <- %s (%d,%d)" % [av_name, bone_map[av_name], av_i, src_i])
                        continue
                map[av_i] = src_i
                src_bind_q[src_i] = (src_skel.get_bone_global_rest(src_i)).basis.get_rotation_quaternion()
                dst_bind_q[av_i] = (avatar_skel.get_bone_global_rest(av_i)).basis.get_rotation_quaternion()
                dst_bind_pos[av_i] = (avatar_skel.get_bone_rest(av_i)).origin
        # bind rotation of the src parent when that parent is NOT a mapped bone
        # (e.g. DEF-hips under the Z-up 'root' bone: carries the -90 deg X rest!)
        var mapped_src: Dictionary = {}
        for av_k in map:
                mapped_src[map[av_k]] = true
        for av_i in map:
                var src_i2: int = map[av_i]
                var sp: int = src_skel.get_bone_parent(src_i2)
                if sp >= 0 and not mapped_src.has(sp):
                        src_parent_bind_q[av_i] = (src_skel.get_bone_global_rest(sp)).basis.get_rotation_quaternion()
        hips_i = avatar_skel.find_bone("Hips")
        # nearest mapped ancestor + fallback parent bind orientation
        for av_i in map:
                var p: int = avatar_skel.get_bone_parent(av_i)
                var anc := -1
                while p >= 0:
                        if map.has(p):
                                anc = p
                                break
                        p = avatar_skel.get_bone_parent(p)
                mapped_ancestor[av_i] = anc
                if anc < 0:
                        var direct: int = avatar_skel.get_bone_parent(av_i)
                        if direct >= 0:
                                dst_parent_bind_q[av_i] = (avatar_skel.get_bone_global_rest(direct)).basis.get_rotation_quaternion()
                        else:
                                dst_parent_bind_q[av_i] = Quaternion.IDENTITY
        order = _topo_order(avatar_skel)
        # scale + hips anchors
        var src_hips_name: String = String(bone_map.get("Hips", ""))
        var src_hips: int = src_skel.find_bone(src_hips_name)
        src_hips_bind_pos = src_skel.get_bone_global_rest(src_hips).origin
        dst_hips_bind_pos = avatar_skel.get_bone_global_rest(hips_i).origin
        var src_parent: int = src_skel.get_bone_parent(src_hips)
        if src_parent >= 0:
                src_root_basis = src_skel.get_bone_global_rest(src_parent).basis
        var dst_parent: int = avatar_skel.get_bone_parent(hips_i)
        if dst_parent >= 0:
                dst_root_basis_inv = avatar_skel.get_bone_global_rest(dst_parent).basis.inverse()
        scale = dst_hips_bind_pos.y / maxf(0.01, src_hips_bind_pos.y)

func _topo_order(skel: Skeleton3D) -> Array:
        var out: Array = []
        var placed: Dictionary = {}
        for av_i in map:
                var chain: Array = []
                var cur: int = av_i
                while cur >= 0 and not placed.has(cur):
                        chain.push_front(cur)
                        placed[cur] = true
                        cur = skel.get_bone_parent(cur)
                for c in chain:
                        if map.has(c) and not out.has(c):
                                out.append(c)
        return out

static func _find_type(node: Node, type: String) -> Node:
        if node.is_class(type):
                return node
        for c in node.get_children():
                var r := _find_type(c, type)
                if r != null:
                        return r
        return null

func has_anim(name: String) -> bool:
        return player.has_animation(name)

func anim_length(name: String) -> float:
        return player.get_animation(name).length

## Sample one clip at time t. Returns { avatar_idx: {"q": Quaternion, "p": Vector3} }
func sample(anim: String, t: float) -> Dictionary:
        if player.assigned_animation != anim:
                player.current_animation = anim
                player.stop()
        var tt := fmod(t, maxf(0.01, anim_length(anim)))
        player.seek(tt, true, true)
        var out: Dictionary = {}
        var wa_src: Dictionary = {}    # src idx -> animated world quat
        var wa_dst: Dictionary = {}    # avatar idx -> animated world quat
        for av_i in order:
                var src_i: int = map[av_i]
                var l_src: Quaternion = src_skel.get_bone_pose_rotation(src_i)
                var src_parent: int = src_skel.get_bone_parent(src_i)
                var parent_q_src: Quaternion
                if wa_src.has(src_parent):
                        parent_q_src = wa_src[src_parent]
                else:
                        parent_q_src = src_parent_bind_q.get(av_i, Quaternion.IDENTITY)
                var w_src := parent_q_src * l_src
                wa_src[src_i] = w_src
                var d := w_src * (src_bind_q[src_i] as Quaternion).inverse()
                var w_dst := d * (dst_bind_q[av_i] as Quaternion)
                wa_dst[av_i] = w_dst
                var anc: int = mapped_ancestor.get(av_i, -1)
                var p_q: Quaternion
                if anc >= 0:
                        p_q = wa_dst[anc]
                else:
                        p_q = dst_parent_bind_q.get(av_i, Quaternion.IDENTITY)
                var l_dst := p_q.inverse() * w_dst
                var pos: Vector3 = dst_bind_pos[av_i]
                if av_i == hips_i:
                        var src_local_p: Vector3 = src_skel.get_bone_pose_position(src_i)
                        var delta_local := src_local_p - (src_skel.get_bone_rest(src_i)).origin
                        var delta_world := src_root_basis * delta_local
                        delta_world.x = 0.0
                        delta_world.z = 0.0
                        pos = dst_bind_pos[av_i] + (dst_root_basis_inv * (delta_world * scale))
                out[av_i] = {"q": l_dst, "p": pos}
        return out
