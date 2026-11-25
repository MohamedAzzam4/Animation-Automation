extends SceneTree
# Verify avatar facing (head world axes) at bind vs retargeted Idle.

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
	var head: int = skel.find_bone("Head")
	var hips: int = skel.find_bone("Hips")

	func_axes("bind", skel, head, hips)
	for i in range(60):
		bd.tick(1.0 / 30.0)
	func_axes("idle@2s", skel, head, hips)
	bd.set_clip("UAL1_Walk", 12)
	for i in range(60):
		bd.tick(1.0 / 30.0)
	func_axes("walk@2s", skel, head, hips)
	quit(0)

func func_axes(tag: String, skel: Skeleton3D, head: int, hips: int) -> void:
	# world transform of a bone ~= skeleton.global_transform * global_pose; skeleton at origin
	var hg := skel.get_bone_global_pose(head)
	var hgz: Vector3 = hg.basis.z
	var hgy: Vector3 = hg.basis.y
	var pg := skel.get_bone_global_pose(hips)
	print(tag, " head_z=", Vector3(snappedf(hgz.x, 0.01), snappedf(hgz.y, 0.01), snappedf(hgz.z, 0.01)),
		" head_y=", Vector3(snappedf(hgy.x, 0.01), snappedf(hgy.y, 0.01), snappedf(hgy.z, 0.01)),
		" hips_z=", Vector3(snappedf(pg.basis.z.x, 0.01), snappedf(pg.basis.z.y, 0.01), snappedf(pg.basis.z.z, 0.01)))
