extends Node3D
## Phase 5/6/7 scene shell: Director + avatar + env, driven by --sched.

var avatar: VRMAvatar = null
var body: BodyDriver = null
var face: FaceDriver = null
var director: Director = null

func _process(delta: float) -> void:
	if director == null:
		avatar = get_node("Avatar") as VRMAvatar
		body = get_node("BodyDriver") as BodyDriver
		face = get_node("FaceDriver") as FaceDriver
		director = get_node("Director") as Director
		var cam := get_node("Camera") as Camera3D
		var lbl: Label = get_node_or_null("UI/ViewLabel")
		director.setup(avatar, body, face, cam, lbl)
		var sched_path := ""
		for arg in OS.get_cmdline_user_args():
			if String(arg).begins_with("--sched="):
				sched_path = String(arg).substr(8)
		if sched_path == "":
			push_error("phase5_scene: missing --sched=<path>")
			get_tree().quit(1)
			return
		director.load_schedule(sched_path)
		print("director loaded: ", sched_path, " frames=", director.total_frames)
	director.tick(delta)
