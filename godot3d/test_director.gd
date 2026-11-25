extends SceneTree
# Smoke test the director against the phase5 schedule (pose sanity only).
func _init() -> void:
	var root := Node3D.new()
	get_root().add_child(root)
	var avatar := VRMAvatar.new()
	root.add_child(avatar)
	avatar._ready()
	var bd := BodyDriver.new()
	root.add_child(bd)
	var fd := FaceDriver.new()
	root.add_child(fd)
	var dir := Director.new()
	root.add_child(dir)
	var cam := Camera3D.new()
	root.add_child(cam)
	dir.setup(avatar, bd, fd, cam, null)
	dir.load_schedule("/home/z/my-project/work/language-video-workflow/output3d/phase5/interaction_schedule.json")
	print("frames=", dir.total_frames, " env=", dir.env_name, " objects=", dir.objects.keys())
	for i in range(dir.total_frames):
		dir.tick(1.0 / 30.0)
		if i % 180 == 0:
			print("f", i, " pos=", avatar.global_position, " yaw=", roundf(rad_to_deg(avatar.rotation.y)))
	quit(0)
