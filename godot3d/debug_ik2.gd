extends SceneTree
func _init() -> void:
	var root := Node3D.new()
	get_root().add_child(root)
	var avatar := VRMAvatar.new()
	root.add_child(avatar)
	avatar._ready()
	var bd := BodyDriver.new()
	root.add_child(bd)
	bd.setup(avatar)
	var skel := avatar.skeleton
	bd.set_clip("UAL1_Sitting_Idle", 6)
	for i in range(60):
		bd.tick(1.0 / 30.0)
	var proc = bd._proc
	var cache: Dictionary = {}
	var head_pos: Vector3 = proc._live_global(skel, skel.find_bone("Head"), cache).origin
	var side := "Right"
	var up_i := skel.find_bone(side + "UpperArm")
	var lo_i := skel.find_bone(side + "LowerArm")
	var sh_i := skel.find_bone(side + "Shoulder")
	var hand_i := skel.find_bone(side + "Hand")
	var up_pos: Vector3 = proc._live_global(skel, up_i, cache).origin
	var bind_up: Vector3 = skel.get_bone_global_rest(up_i).origin
	var bind_lo: Vector3 = skel.get_bone_global_rest(lo_i).origin
	var bind_hand: Vector3 = skel.get_bone_global_rest(hand_i).origin
	var a := bind_up.distance_to(bind_lo)
	var bl := bind_lo.distance_to(bind_hand)
	var target := head_pos + Vector3(0.0, -0.36, 0.34) + Vector3(-0.12, 0, 0)
	print("head=", head_pos, " up_pos=", up_pos)
	print("bind_up=", bind_up, " bind_lo=", bind_lo, " bind_hand=", bind_hand)
	print("a=", a, " bl=", bl, " target=", target, " dist=", up_pos.distance_to(target))
	var d := clampf(up_pos.distance_to(target), absf(bl - a) + 0.015, a + bl - 0.015)
	var dir := (target - up_pos).normalized()
	var cos_a := clampf((a * a + d * d - bl * bl) / (2.0 * a * d), -1.0, 1.0)
	var ang := acos(cos_a)
	var bend := dir.cross(Vector3(-0.5, -1, -0.3).normalized())
	bend = bend.normalized()
	var upper_dir := (dir.rotated(bend, ang)).normalized()
	print("d=", d, " dir=", dir, " ang_deg=", rad_to_deg(ang))
	print("bend=", bend, " upper_dir=", upper_dir)
	var q_up := proc._dir_quat(skel, up_i, upper_dir)
	var q_sh: Quaternion = proc._live_global(skel, sh_i, cache).basis.get_rotation_quaternion()
	var local_up := q_sh.inverse() * q_up
	skel.set_bone_pose_rotation(up_i, local_up)
	var cache2: Dictionary = {}
	print("upper arm new world dir check: hand... lower arm pos after = ", proc._live_global(skel, lo_i, cache2).origin)
	print("elbow should be at ", up_pos + upper_dir * a)
	quit(0)
