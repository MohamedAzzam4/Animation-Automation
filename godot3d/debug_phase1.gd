extends SceneTree
# Debug: manually step phase1 camera to verify view switching.

func _init() -> void:
        var ps: PackedScene = load("res://phase1.tscn")
        var scene := ps.instantiate()
        get_root().add_child(scene)
        var cam: Camera3D = scene.get_node("Camera")
        var label: Label = scene.get_node("UI/ViewLabel")
        var checks := [37, 112, 187, 262, 337, 412]
        var frame := 0
        for i in range(450):
                cam._process(1.0 / 30.0)
                frame += 1
                if frame in checks:
                        print("frame ", frame, " pos=", cam.position, " fov=", cam.fov,
                                " label=", label.text.replace("\n", " | "))
        quit(0)
