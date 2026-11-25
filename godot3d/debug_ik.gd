extends SceneTree
# Numeric IK debug: seated hold_book — where do the hands actually end up?

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
	skel.force_update_all_bone_transforms()
	var head_i := skel.find_bone("Head")
	var up_i := skel.find_bone("RightUpperArm")
	var hand_i := skel.find_bone("RightHand")
	var proc = bd._proc
	var cache: Dictionary = {}
	print("seated head_pos(mfk)=", proc._live_global(skel, head_i, cache).origin)
	print("seated hand_pos(mfk before)=", proc._live_global(skel, hand_i, cache).origin)
	proc.post_ik(skel, "hold_book", 2.2)
	var cache2: Dictionary = {}
	print("after ik hand_pos(mfk)=", proc._live_global(skel, hand_i, cache2).origin)
	# component dumps
	var tgt := skel.get_bone_global_pose(head_i).origin + Vector3(0.0, -0.34, 0.34) + Vector3(0.13, 0, 0)
	print("expected target=", tgt)
	quit(0)
