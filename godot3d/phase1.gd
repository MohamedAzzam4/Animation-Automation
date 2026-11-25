extends Camera3D
## Phase 1: six-view turntable inspection of AvatarSample_B.
## Pure function of the frame counter (Movie Maker fixed fps).

const FPS := 30
const HOLD := 75  # 2.5 s per view

const VIEWS := [
        {"name": "FRONT (bind pose)", "yaw": 0.0, "dist": 2.35, "height": 1.22, "fov": 45.0},
        {"name": "THREE-QUARTER", "yaw": 42.0, "dist": 2.35, "height": 1.22, "fov": 45.0},
        {"name": "SIDE", "yaw": 90.0, "dist": 2.35, "height": 1.22, "fov": 45.0},
        {"name": "BACK", "yaw": 180.0, "dist": 2.35, "height": 1.22, "fov": 45.0},
        {"name": "FACE CLOSE-UP", "yaw": 14.0, "dist": 0.62, "height": 1.30, "fov": 28.0},
        {"name": "FULL BODY", "yaw": -28.0, "dist": 3.35, "height": 1.0, "fov": 40.0},
]

var frame := 0
var avatar: VRMAvatar = null
var label: Label = null

func _setup() -> void:
        if avatar != null:
                return
        avatar = get_node("../Avatar") as VRMAvatar
        label = get_node("../UI/ViewLabel") as Label
        if avatar == null or label == null:
                push_error("phase1: Avatar/Label not found under " + str(get_parent().get_path()))

func _process(_delta: float) -> void:
        _setup()
        var vi := clampi(frame / HOLD, 0, VIEWS.size() - 1)
        var local := frame - vi * HOLD
        var cur: Dictionary = VIEWS[vi]
        var prev: Dictionary = VIEWS[maxi(0, vi - 1)] if local < 15 and vi > 0 else cur
        var u := smoothstep(0.0, 1.0, clampf(local / 15.0, 0.0, 1.0)) if vi > 0 else 1.0
        var yaw: float = lerp(float(prev["yaw"]), float(cur["yaw"]), u)
        var dist: float = lerp(float(prev["dist"]), float(cur["dist"]), u)
        var height: float = lerp(float(prev["height"]), float(cur["height"]), u)
        fov = lerp(float(prev["fov"]), float(cur["fov"]), u)
        var a := deg_to_rad(yaw)
        var origin := avatar.global_position
        position = origin + Vector3(sin(a) * dist, height - 0.0, cos(a) * dist)
        if cur["name"] == "FACE CLOSE-UP":
                look_at(avatar.face_position() + Vector3(0, 0.02, 0), Vector3.UP)
        else:
                look_at(origin + Vector3(0, height * 0.82, 0), Vector3.UP)
        label.text = "PHASE 1  AvatarSample_B (VRM 0.x, MToon)\nVIEW %d/6: %s" % [vi + 1, cur["name"]]
        frame += 1
