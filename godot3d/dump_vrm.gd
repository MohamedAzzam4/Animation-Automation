extends SceneTree
# Phase 1: runtime inspection of AvatarSample_B.vrm and the two UAL GLBs.
# Dumps skeleton, blend shapes, materials, animations -> character_capabilities.json

const OUT := "/home/z/my-project/work/language-video-workflow/output3d/phase1/character_capabilities.json"
const VRM_PATH := "res://assets3d/AvatarSample_B.vrm"
const UAL1_PATH := "res://assets3d/UAL1.glb"
const UAL2_PATH := "res://assets3d/UAL2.glb"

func _find_nodes(node: Node, types: Array, out: Array, depth: int = 0) -> void:
	if depth > 12:
		return
	for t in types:
		if node.is_class(t):
			out.append(node)
			break
	for c in node.get_children():
		_find_nodes(c, types, out, depth + 1)

func _dump_skeleton(sk: Skeleton3D) -> Dictionary:
	var bones := []
	for i in sk.get_bone_count():
		var rest := sk.get_bone_rest(i)
		var gp := sk.get_bone_global_rest(i)
		bones.append({
			"index": i,
			"name": sk.get_bone_name(i),
			"parent": sk.get_bone_parent(i),
			"parent_name": sk.get_bone_name(sk.get_bone_parent(i)) if sk.get_bone_parent(i) >= 0 else "",
			"rest_pos": [rest.origin.x, rest.origin.y, rest.origin.z],
			"rest_quat": [rest.basis.x.x, rest.basis.x.y, rest.basis.x.z,
				rest.basis.y.x, rest.basis.y.y, rest.basis.y.z,
				rest.basis.z.x, rest.basis.z.y, rest.basis.z.z],
			"global_rest_y": gp.origin.y,
		})
	return {"bone_count": sk.get_bone_count(), "bones": bones}

func _dump_meshes(root: Node) -> Array:
	var meshes := []
	var mis: Array = []
	_find_nodes(root, ["MeshInstance3D"], mis)
	for mi in mis:
		var mesh: Mesh = mi.mesh
		if mesh == null:
			continue
		var names := []
		for i in mesh.get_blend_shape_count():
			names.append(mesh.get_blend_shape_name(i))
		var mats := []
		for s in mesh.get_surface_count():
			var mat = mesh.surface_get_material(s)
			mats.append({
				"shader": mat.get("shader").resource_path if mat != null and mat.get("shader") != null else str(mat.get_class()) if mat != null else "null",
				"class": mat.get_class() if mat != null else "null",
			})
		var aabb: AABB = mesh.get_aabb()
		meshes.append({
			"node": str(mi.get_path_to(root)) if mi != root else ".",
			"surface_count": mesh.get_surface_count(),
			"blend_shape_count": mesh.get_blend_shape_count(),
			"blend_shapes": names,
			"materials": mats,
			"aabb_size": [aabb.size.x, aabb.size.y, aabb.size.z],
		})
	return meshes

func _dump_anim_player(root: Node) -> Dictionary:
	var players: Array = []
	_find_nodes(root, ["AnimationPlayer"], players)
	if players.is_empty():
		return {"players": []}
	var out_players := []
	for p in players:
		var anims := []
		var lib: AnimationLibrary = p.get_animation_library("")
		if lib != null:
			for name in lib.get_animation_list():
				var a: Animation = lib.get_animation(name)
				var track_types := {}
				for t in a.get_track_count():
					var tt := a.track_get_type(t)
					track_types[tt] = track_types.get(tt, 0) + 1
				anims.append({
					"name": name,
					"length": a.length,
					"loop": a.loop_mode,
					"tracks": a.get_track_count(),
					"track_types": track_types,
				})
		out_players.append({"path": str(p.get_path_to(root)), "root_node": str(p.root_node), "animations": anims})
	return {"players": out_players}

func _inspect_scene(res_path: String) -> Dictionary:
	var ps: PackedScene = load(res_path)
	if ps == null:
		return {"error": "load failed: " + res_path}
	var inst := ps.instantiate()
	var result := {"resource": res_path}
	var skels: Array = []
	_find_nodes(inst, ["Skeleton3D"], skels)
	if not skels.is_empty():
		result["skeleton"] = _dump_skeleton(skels[0])
		result["skeleton_node"] = str(skels[0].get_path_to(inst))
	result["meshes"] = _dump_meshes(inst)
	result["animation"] = _dump_anim_player(inst)
	# root-level properties of interest (vrm meta etc.)
	var props := []
	for prop in ["vrm_meta", "vrm_secondary", "animation_player"]:
		var v = inst.get(prop)
		if v != null:
			props.append(prop)
	result["root_props"] = props
	var meta = inst.get("vrm_meta")
	if meta != null:
		var md := {}
		for key in ["title", "author", "contact_information", "reference", "allowed_user", "license_name", "commercial_use", "modification"]:
			var v = meta.get(key)
			if v != null:
				md[key] = str(v)
		result["vrm_meta"] = md
	inst.queue_free()
	return result

func _init() -> void:
	var os_dir := OUT.get_base_dir()
	DirAccess.make_dir_recursive_absolute(os_dir)
	var caps := {
		"schema": "capability_catalog_v1",
		"generated_by": "phase1 dump_vrm.gd (runtime inspection)",
		"engine": Engine.get_version_info().string,
		"vrm_addon": "godot-vrm e15199f980064028bfa4fbee5e70dddb82dd55c3",
		"avatar": _inspect_scene(VRM_PATH),
		"ual1": _inspect_scene(UAL1_PATH),
		"ual2": _inspect_scene(UAL2_PATH),
	}
	var f := FileAccess.open(OUT, FileAccess.WRITE)
	f.store_string(JSON.stringify(caps, "  "))
	f.close()
	print("WROTE ", OUT)
	# console summary
	print("avatar bones: ", caps.avatar.get("skeleton", {}).get("bone_count", 0))
	print("avatar meshes: ", caps.avatar.get("meshes", []).size())
	var bs := {}
	for m in caps.avatar.get("meshes", []):
		for n in m.get("blend_shapes", []):
			bs[n] = true
	print("avatar blend shape names: ", bs.keys())
	for u in ["ual1", "ual2"]:
		var an := []
		for p in caps[u].get("animation", {}).get("players", []):
			for a in p.get("animations", []):
				an.append("%s(%.2fs)" % [a.name, a.length])
		print(u, " skeleton bones: ", caps[u].get("skeleton", {}).get("bone_count", 0))
		print(u, " animations: ", an)
	quit(0)
