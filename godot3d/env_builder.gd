class_name EnvBuilder
## Deterministic procedural environments with named anchors.
## All geometry is simple colored primitives — no external assets, no physics,
## no RNG (or seeded via the schedule seed only).

const ENV_ANCHORS := {
	"test_room": {
		"chair": [-0.75, 0.0, 0.22], "mug": [-0.85, 0.74, 0.86],
		"book": [-0.55, 0.74, 0.88], "table": [-0.75, 0.95, 1.05],
		"door": [1.6, 0.0, 0.6],
	},
	"student_room": {
		"chair": [-0.75, 0.0, 0.22], "chair_approach": [-0.75, 0.0, 0.58],
		"mug": [-0.85, 0.74, 0.86], "book": [-0.55, 0.74, 0.88],
		"table": [-0.75, 0.95, 1.05], "door": [1.6, 0.0, 0.6],
		"window": [-2.9, 1.4, 0.6], "forward": [0.0, 1.5, 2.5],
	},
	"hallway": {
		"door": [0.0, 0.0, -3.4], "forward": [0.0, 1.5, -2.0],
	},
	"cafe": {
		"chair": [-1.2, 0.0, 1.42], "chair_approach": [-1.2, 0.0, 1.55],
		"mug": [-1.34, 0.79, 0.5], "book": [-1.06, 0.79, 0.5],
		"table": [-1.2, 0.95, 0.6], "door": [2.9, 0.0, -1.0],
		"window": [0.5, 1.45, -2.4], "forward": [0.0, 1.5, 2.0],
	},
	"park": {
		"bench": [0.9, 1.0, 1.4], "trees": [-3.2, 1.4, -2.0],
		"door": [9.0, 0.0, 9.0], "forward": [0.0, 1.5, -2.0],
	},
}

static func anchors_of(env: String) -> Dictionary:
	return ENV_ANCHORS.get(env, {})

func build(env: String) -> Node3D:
	var root := Node3D.new()
	root.name = "Env_" + env
	match env:
		"test_room":
			_build_room(root, Color(0.72, 0.66, 0.58), 7.0, 5.5, true, true)
			_furniture_desk_set(root, "test_room")
		"student_room":
			_build_room(root, Color(0.7, 0.64, 0.56), 8.0, 6.0, true, true)
			_furniture_desk_set(root, "student_room")
			_window(root, Vector3(-3.93, 1.4, 0.6), 1.4, 1.3)
			_bed(root, Vector3(2.3, 0.0, -1.6))
			_shelf(root, Vector3(-1.0, 0.0, -2.6))
			_rug(root, Vector3(0.2, 0.0, 1.6), 1.8, 1.2, Color(0.6, 0.35, 0.3))
		"hallway":
			_build_hallway(root)
		"cafe":
			_build_cafe(root)
		"park":
			_build_park(root)
		_:
			push_error("EnvBuilder: unknown environment '%s'" % env)
	return root

# ---------------- primitives ----------------

func _mat(c: Color, rough := 0.9) -> StandardMaterial3D:
	var m := StandardMaterial3D.new()
	m.albedo_color = c
	m.roughness = rough
	return m

func _box(parent: Node3D, size: Vector3, pos: Vector3, c: Color, name_s := "Box") -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var mesh := BoxMesh.new()
	mesh.size = size
	mesh.material = _mat(c)
	mi.mesh = mesh
	mi.position = pos
	mi.name = name_s
	parent.add_child(mi)
	return mi

func _cyl(parent: Node3D, r: float, h: float, pos: Vector3, c: Color, name_s := "Cyl") -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var mesh := CylinderMesh.new()
	mesh.top_radius = r
	mesh.bottom_radius = r
	mesh.height = h
	mesh.material = _mat(c)
	mi.mesh = mesh
	mi.position = pos
	mi.name = name_s
	parent.add_child(mi)
	return mi

func _sphere(parent: Node3D, r: float, pos: Vector3, c: Color, name_s := "Sph") -> MeshInstance3D:
	var mi := MeshInstance3D.new()
	var mesh := SphereMesh.new()
	mesh.radius = r
	mesh.height = r * 2.0
	mesh.material = _mat(c)
	mi.mesh = mesh
	mi.position = pos
	mi.name = name_s
	parent.add_child(mi)
	return mi

# ---------------- shared pieces ----------------

func _floor(parent: Node3D, w: float, d: float, c: Color) -> void:
	_box(parent, Vector3(w, 0.1, d), Vector3(0, -0.05, 0), c, "Floor")

func _walls(parent: Node3D, w: float, d: float, h: float, c: Color) -> void:
	_box(parent, Vector3(w, h, 0.12), Vector3(0, h / 2.0, -d / 2.0), c, "WallBack")
	_box(parent, Vector3(0.12, h, d), Vector3(-w / 2.0, h / 2.0, 0), c, "WallLeft")
	_box(parent, Vector3(0.12, h, d), Vector3(w / 2.0, h / 2.0, 0), c, "WallRight")
	_box(parent, Vector3(w, h, 0.12), Vector3(0, h / 2.0, d / 2.0), c, "WallFront")

func _build_room(root: Node3D, floor_c: Color, w: float, d: float, _win: bool, _dr: bool) -> void:
	_floor(root, w, d, floor_c)
	_walls(root, w, d, 3.0, Color(0.82, 0.8, 0.76))
	_box(root, Vector3(w, 0.25, 0.2), Vector3(0, 3.0, -d / 2.0), Color(0.55, 0.45, 0.4), "Trim")

func _table(parent: Node3D, top_pos: Vector3, w: float, d: float) -> void:
	var h := top_pos.y
	_box(parent, Vector3(w, 0.05, d), top_pos, Color(0.62, 0.42, 0.28), "TableTop")
	for x in [-w / 2.0 + 0.06, w / 2.0 - 0.06]:
		for z in [-d / 2.0 + 0.06, d / 2.0 - 0.06]:
			_box(parent, Vector3(0.06, h, 0.06), Vector3(top_pos.x + x, h / 2.0, top_pos.z + z), Color(0.42, 0.3, 0.2), "TableLeg")

func _chair(parent: Node3D, pos: Vector3, c := Color(0.5, 0.34, 0.22)) -> Dictionary:
	# seat 0.47 high, facing +Z (back at -Z of seat center)
	var seat_y := 0.47
	_box(parent, Vector3(0.46, 0.06, 0.46), Vector3(pos.x, seat_y, pos.z), c, "ChairSeat")
	_box(parent, Vector3(0.46, 0.55, 0.06), Vector3(pos.x, seat_y + 0.3, pos.z - 0.23), c, "ChairBack")
	for lx in [-0.18, 0.18]:
		for lz in [-0.18, 0.18]:
			_box(parent, Vector3(0.05, seat_y, 0.05), Vector3(pos.x + lx, seat_y / 2.0, pos.z + lz), Color(0.32, 0.22, 0.15), "ChairLeg")
	return {"seat_top": seat_y}

func _door(parent: Node3D, pos: Vector3, open_deg := 0.0) -> Node3D:
	# frame at pos (floor), panel hinged on its -X edge, opens around Y
	_box(parent, Vector3(0.1, 2.15, 0.16), Vector3(pos.x - 0.5, 1.07, pos.z), Color(0.75, 0.72, 0.68), "DoorFrameL")
	_box(parent, Vector3(0.1, 2.15, 0.16), Vector3(pos.x + 0.5, 1.07, pos.z), Color(0.75, 0.72, 0.68), "DoorFrameR")
	_box(parent, Vector3(1.1, 0.12, 0.16), Vector3(pos.x, 2.13, pos.z), Color(0.75, 0.72, 0.68), "DoorFrameTop")
	var hinge := Node3D.new()
	hinge.name = "DoorHinge"
	hinge.position = Vector3(pos.x - 0.45, 0, pos.z)
	parent.add_child(hinge)
	var panel := _box(hinge, Vector3(0.9, 2.05, 0.07), Vector3(0.45, 1.025, 0), Color(0.58, 0.4, 0.26), "DoorPanel")
	_sphere(hinge, 0.05, Vector3(0.82, 1.0, 0.07), Color(0.85, 0.75, 0.3), "DoorKnob")
	hinge.rotation.y = deg_to_rad(open_deg)
	return hinge

func _mug(parent: Node3D, pos: Vector3) -> MeshInstance3D:
	var mug := _cyl(parent, 0.045, 0.1, pos + Vector3(0, 0.05, 0), Color(0.85, 0.3, 0.25), "Mug")
	_cyl(parent, 0.036, 0.005, pos + Vector3(0, 0.101, 0), Color(0.55, 0.35, 0.2), "MugCoffee")
	return mug

func _book(parent: Node3D, pos: Vector3) -> MeshInstance3D:
	var b := _box(parent, Vector3(0.17, 0.035, 0.23), pos + Vector3(0, 0.018, 0), Color(0.2, 0.35, 0.6), "Book")
	_box(parent, Vector3(0.15, 0.037, 0.21), pos + Vector3(0.012, 0.018, 0), Color(0.95, 0.94, 0.9), "BookPages")
	return b

func _window(parent: Node3D, pos: Vector3, w: float, h: float) -> void:
	_box(parent, Vector3(0.08, h + 0.16, w + 0.16), pos, Color(0.75, 0.72, 0.68), "WindowFrame")
	var glass := _box(parent, Vector3(0.02, h, w), pos + Vector3(0.02, 0, 0), Color(0.65, 0.8, 0.95), "WindowGlass")
	glass.set_instance_shader_parameter("emission", null)
	var m: StandardMaterial3D = glass.mesh.material
	m.emission_enabled = true
	m.emission = Color(0.5, 0.65, 0.8)
	m.emission_energy_multiplier = 0.6

func _bed(parent: Node3D, pos: Vector3) -> void:
	_box(parent, Vector3(1.0, 0.3, 2.1), pos + Vector3(0, 0.15, 0), Color(0.55, 0.38, 0.26), "BedFrame")
	_box(parent, Vector3(0.95, 0.18, 2.0), pos + Vector3(0, 0.38, 0), Color(0.9, 0.9, 0.92), "Mattress")
	_box(parent, Vector3(0.95, 0.3, 2.0), pos + Vector3(0, 0.35, -0.9), Color(0.45, 0.55, 0.75), "Blanket")
	_box(parent, Vector3(0.7, 0.12, 0.45), pos + Vector3(0, 0.5, -0.75), Color(1, 1, 1), "Pillow")

func _shelf(parent: Node3D, pos: Vector3) -> void:
	_box(parent, Vector3(1.6, 1.9, 0.35), pos + Vector3(0, 0.95, 0), Color(0.5, 0.36, 0.24), "Shelf")
	for i in range(4):
		_box(parent, Vector3(1.5, 0.05, 0.3), pos + Vector3(0, 0.3 + i * 0.45, 0.01), Color(0.6, 0.45, 0.3), "ShelfBoard")
	for i in range(9):
		var c := Color(0.3 + 0.06 * (i % 4), 0.3 + 0.05 * (i % 3), 0.55 - 0.04 * (i % 5))
		_box(parent, Vector3(0.09, 0.24, 0.2), pos + Vector3(-0.65 + 0.16 * (i % 8), 0.47 + 0.45 * (i / 8), 0.02), c, "ShelfBook%d" % i)

func _rug(parent: Node3D, pos: Vector3, w: float, d: float, c: Color) -> void:
	var r := _box(parent, Vector3(w, 0.02, d), pos + Vector3(0, 0.01, 0), c, "Rug")
	var m: StandardMaterial3D = r.mesh.material
	m.roughness = 1.0

func _lamp(parent: Node3D, pos: Vector3, warm := true) -> OmniLight3D:
	var l := OmniLight3D.new()
	l.position = pos
	l.omni_range = 4.0
	l.light_energy = 0.7
	l.light_color = Color(1.0, 0.85, 0.65) if warm else Color(0.8, 0.9, 1.0)
	l.shadow_enabled = false
	parent.add_child(l)
	_sphere(parent, 0.09, pos, Color(1.0, 0.9, 0.7), "LampBulb")
	return l

func _tree(parent: Node3D, pos: Vector3, s := 1.0) -> void:
	_cyl(parent, 0.12 * s, 1.6 * s, pos + Vector3(0, 0.8 * s, 0), Color(0.4, 0.28, 0.18), "Trunk")
	_sphere(parent, 0.75 * s, pos + Vector3(0, 1.9 * s, 0), Color(0.28, 0.55, 0.3), "Foliage")
	_sphere(parent, 0.5 * s, pos + Vector3(0.45 * s, 1.5 * s, 0.2 * s), Color(0.32, 0.6, 0.33), "Foliage2")

func _furniture_desk_set(root: Node3D, env: String) -> void:
	# NOTE: mug/book are spawned by the Director from the schedule objects,
	# never placed here (avoids duplicate props).
	var a: Dictionary = ENV_ANCHORS[env]
	var table_pos: Vector3 = Vector3(a["table"][0], 0.72, a["table"][2])
	_table(root, table_pos, 1.1, 0.62)
	_chair(root, Vector3(a["chair"][0], 0, a["chair"][2]))
	_door(root, Vector3(a["door"][0], 0, a["door"][2]), 0.0)
	_lamp(root, Vector3(2.2, 2.4, 1.6))

func _build_hallway(root: Node3D) -> void:
	_floor(root, 3.2, 11.0, Color(0.55, 0.5, 0.45))
	_box(root, Vector3(3.2, 0.02, 8.0), Vector3(0, 0.011, -0.5), Color(0.6, 0.22, 0.2), "Runner")
	_walls(root, 3.2, 11.0, 3.0, Color(0.85, 0.82, 0.78))
	_door(root, Vector3(0, 0, -5.45), 0.0)
	for z in [-3.0, -1.0, 1.0, 3.0]:
		_lamp(root, Vector3(-1.5, 2.5, z))
		_lamp(root, Vector3(1.5, 2.5, z + 0.5))
	for i in range(4):
		_box(root, Vector3(0.5, 1.7, 0.06), Vector3(-1.55, 0.85, -2.0 + i * 1.4), Color(0.7, 0.75, 0.8), "PanelL%d" % i)

func _build_cafe(root: Node3D) -> void:
	_floor(root, 8.0, 8.0, Color(0.45, 0.36, 0.3))
	_walls(root, 8.0, 8.0, 3.2, Color(0.78, 0.68, 0.58))
	# counter along back
	_box(root, Vector3(5.0, 1.05, 0.7), Vector3(0.5, 0.525, -3.3), Color(0.5, 0.32, 0.22), "Counter")
	_box(root, Vector3(5.2, 0.06, 0.85), Vector3(0.5, 1.06, -3.3), Color(0.68, 0.5, 0.35), "CounterTop")
	# window front-left
	_window(root, Vector3(0.5, 1.6, -3.85), 2.2, 1.4)
	# seating set (schedule anchors)
	var a: Dictionary = ENV_ANCHORS["cafe"]
	_table(root, Vector3(a["table"][0], 0.72, a["table"][2] - 0.4), 0.8, 0.8)
	_chair(root, Vector3(a["chair"][0], 0, a["chair"][2]), Color(0.42, 0.3, 0.2))
	# two extra tables
	for tp in [[1.3, 1.2], [2.4, -0.8]]:
		_table(root, Vector3(float(tp[0]) * -1.0 + 2.6, 0.72, float(tp[1])), 0.75, 0.75)
		_chair(root, Vector3(float(tp[0]) * -1.0 + 2.6, 0, float(tp[1]) + 0.62), Color(0.42, 0.3, 0.2))
	# pendant lamps
	for lp in [[-1.2, 0.4], [1.0, 0.9], [0.4, -2.6]]:
		_lamp(root, Vector3(float(lp[0]), 2.3, float(lp[1])))
		_cyl(root, 0.02, 0.7, Vector3(float(lp[0]), 2.65, float(lp[1])), Color(0.2, 0.2, 0.22), "Cord")

func _build_park(root: Node3D) -> void:
	_floor(root, 22.0, 22.0, Color(0.42, 0.6, 0.34))
	# winding path
	for i in range(9):
		_box(root, Vector3(1.4, 0.02, 1.4), Vector3(-3.0 + i * 0.9, 0.011, 3.0 - i * 0.75), Color(0.72, 0.66, 0.52), "Path%d" % i)
	# bench
	var bp := Vector3(0.9, 0, 1.4)
	_box(root, Vector3(1.6, 0.07, 0.5), bp + Vector3(0, 0.45, 0), Color(0.5, 0.35, 0.22), "BenchSeat")
	_box(root, Vector3(1.6, 0.5, 0.07), bp + Vector3(0, 0.72, -0.22), Color(0.5, 0.35, 0.22), "BenchBack")
	for lx in [-0.65, 0.65]:
		_box(root, Vector3(0.08, 0.45, 0.45), bp + Vector3(lx, 0.225, 0), Color(0.3, 0.3, 0.32), "BenchLeg")
	# trees
	for tp in [[-3.2, -2.0, 1.2], [-4.5, 1.5, 0.9], [3.8, -2.6, 1.4], [4.6, 1.8, 1.0], [-2.0, 4.2, 0.8], [2.9, 4.6, 1.1]]:
		_tree(root, Vector3(float(tp[0]), 0, float(tp[1])), float(tp[2]))
	# bushes
	for bp2 in [[-1.4, 0.6], [2.0, 0.9], [1.2, -1.8]]:
		_sphere(root, 0.4, Vector3(float(bp2[0]), 0.3, float(bp2[1])), Color(0.3, 0.52, 0.3), "Bush")
