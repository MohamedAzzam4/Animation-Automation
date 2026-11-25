extends SceneTree
# Smoke test: retarget Idle/Walk/Sitting for a few seconds, check for NaN/garbage.

func _init() -> void:
        var root := Node3D.new()
        get_root().add_child(root)
        var avatar := VRMAvatar.new()
        root.add_child(avatar)
        avatar._ready()  # --script harness never fires NOTIFICATION_READY
        var bd := BodyDriver.new()
        root.add_child(bd)
        bd.setup(avatar)
        print("clips: ", bd.CLIP_SOURCES.keys())
        print("UAL1 Idle len=", bd.clip_length("UAL1_Idle"), " Walk len=", bd.clip_length("UAL1_Walk"))
        var skel := avatar.skeleton
        var hips: int = skel.find_bone("Hips")
        var lfoot: int = skel.find_bone("LeftFoot")

        for clip_name in ["UAL1_Idle", "UAL1_Walk", "UAL1_Sitting_Idle", "UAL2_Yes", "proc_wave", "proc_think"]:
                bd.set_clip(String(clip_name), 6)
                var last_y := 0.0
                for i in range(90):
                        bd.tick(1.0 / 30.0)
                        last_y = skel.get_bone_pose_position(hips).y
                var q: Quaternion = skel.get_bone_pose_rotation(hips)
                var foot_pos: Vector3 = skel.get_bone_pose_position(lfoot)
                var bad := is_nan(last_y) or is_nan(q.x) or is_nan(foot_pos.x)
                print("%-22s hips_y=%.3f foot_local=%s quat_ok=%s %s" % [
                        clip_name, last_y, Vector3(snappedf(foot_pos.x, 0.001), snappedf(foot_pos.y, 0.001), snappedf(foot_pos.z, 0.001)),
                        not bad, "!! NaN" if bad else ""])
        quit(0)
