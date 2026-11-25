extends SceneTree
# Probe UAL1 hips/root transforms during Sitting_Idle + Walk.

func _init() -> void:
	var root := Node3D.new()
	get_root().add_child(root)
	var avatar := VRMAvatar.new()
	root.add_child(avatar)
	avatar._ready()
	var bd := BodyDriver.new()
	root.add_child(bd)
	bd.setup(avatar)
	var skel := bd.rig_ual1.src_skel
	var hips: int = skel.find_bone("DEF-hips")
	var root_idx: int = skel.get_bone_parent(hips)
	print("root bone idx=", root_idx, " name=", skel.get_bone_name(root_idx) if root_idx >= 0 else "-")
	if root_idx >= 0:
		var rr := skel.get_bone_global_rest(root_idx)
		var rl := skel.get_bone_rest(root_idx)
		print("root rest global origin=", rr.origin, " basis_diag=", rr.basis.x.x, ",", rr.basis.y.y, ",", rr.basis.z.z)
		print("root rest local origin=", rl.origin)
	print("hips rest local=", skel.get_bone_rest(hips).origin, " global=", skel.get_bone_global_rest(hips).origin)
	var player := bd.rig_ual1.player
	for anim in ["Sitting_Idle", "Walk", "Idle"]:
		player.current_animation = String(anim)
		player.stop()
		for t in [0.2, 0.6, 1.0, 1.4]:
			player.seek(t, true, true)
			var lp: Vector3 = skel.get_bone_pose_position(hips)
			var lr: Quaternion = skel.get_bone_pose_rotation(hips)
			print(String(anim), " t=", t, " hips_local=", Vector3(snappedf(lp.x, 0.001), snappedf(lp.y, 0.001), snappedf(lp.z, 0.001)),
				" root_pose_pos=", skel.get_bone_pose_position(root_idx) if root_idx >= 0 else Vector3.ZERO)
	quit(0)
