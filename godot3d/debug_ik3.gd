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
	var c := head_pos + Vector3(0.0, -0.36, 0.34)
	print("calling _arm_ik Right with target=", c + Vector3(-0.12, 0, 0))
	proc._arm_ik(skel, "Right", c + Vector3(-0.12, 0, 0), Vector3(-0.5, -1, -0.3), cache)
	var cache2: Dictionary = {}
	print("right hand after _arm_ik=", proc._live_global(skel, skel.find_bone("RightHand"), cache2).origin)
	proc._arm_ik(skel, "Left", c + Vector3(0.12, 0, 0), Vector3(0.5, -1, -0.3), cache)
	var cache3: Dictionary = {}
	print("left hand after _arm_ik=", proc._live_global(skel, skel.find_bone("LeftHand"), cache3).origin)
	print("now via post_ik:")
	proc.post_ik(skel, "hold_book", 2.2)
	var cache4: Dictionary = {}
	print("right hand after post_ik=", proc._live_global(skel, skel.find_bone("RightHand"), cache4).origin)
	print("left hand after post_ik=", proc._live_global(skel, skel.find_bone("LeftHand"), cache4).origin)
	quit(0)
