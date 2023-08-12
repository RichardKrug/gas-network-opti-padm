import math

time_step_unit = "min"

def simple_entry(e):
	return {None: e}

def get_value_in_unit(glp, element, value_key, unit_target, default_value=None):
	if value_key not in element and default_value is not None:
		return default_value
	value = float(element[value_key]["value"])
	if "unit" not in element[value_key]:
		return value
	unit = element[value_key]["unit"]
	return convert_value_to_unit(glp, value, unit, unit_target)

def convert_value_to_unit(glp, value, unit, unit_target):
	if unit == "meter":
		unit = "m"
	if unit_target == "meter":
		unit_target = "m"

	if unit == unit_target:
		return value

	if unit == "1000m_cube_per_hour":
		if unit_target == "kg_per_s":
			norm_density = get_norm_density(glp)
			return norm_density * 1e3 * value / (60 * 60)
	if unit == "km":
		if unit_target == "m":
			return 1e3 * value
	if unit == "m":
		if unit_target == "km":
			return 1e-3 * value
	if unit == "mm":
		if unit_target == "m":
			return 1e-3 * value
	if unit == "bar":
		if unit_target == "pascal":
			return 1e5 * value
	if unit == "s":
		if unit_target == "min":
			return value / 60
		if unit_target == "h":
			return value / (60 * 60)
	if unit == "min":
		if unit_target == "s":
			return value * 60
		if unit_target == "h":
			return value / 60
	if unit == "h":
		if unit_target == "s":
			return value * 60 * 60
		if unit_target == "min":
			return value * 60
	raise Exception("Could not convert " + unit + " to " + unit_target)

def get_norm_density(glp):
	for entry in glp.entries:
		return get_value_in_unit(glp, glp.entries[entry], "normDensity", "kg_per_m_cube")
	raise Exception("Could not find norm density!")

def create_model_instance(args, glp, model, block, stationary_model, tracking_model):
	data = {}
	add_parameters(args, glp, data)
	add_time_grid(args, glp, data)
	add_nodes(args, glp, block, data)
	add_arcs(args, glp, block, data)
	set_inital_values_and_start_point(data, stationary_model)
	if tracking_model:
		set_tracking_parameters(args, data, tracking_model)
	mtype = get_block_mtype(args, block)
	solver = get_block_solver(args, block)
	return model.create_instance(simple_entry(data)), mtype, solver

def create_stationary_model_instance(args, glp, model):
	block = {
		"virtual_arcs": []
	}
	for type in glp.node_types + glp.arc_types:
		block[type] = glp.get_elements(type).keys()
	data = {}
	add_parameters(args, glp, data)
	data["delta_t"] = simple_entry(convert_value_to_unit(glp, args.time_step, time_step_unit, "s"))
	data["t"] = simple_entry([0])
	data["t1"] = simple_entry([0])
	add_nodes(args, glp, block, data)
	add_arcs(args, glp, block, data)
	set_stationary_start_point(data)
	mtype = get_block_mtype(args, block)
	solver = get_block_solver(args, block)
	return model.create_instance(simple_entry(data)), mtype, solver

def add_parameters(args, glp, data):
	sound_speed = convert_value_to_unit(glp, glp.scenario["sound_speed"], glp.scenario["units"]["sound_speed"], "m_per_s")
	data["c"] = simple_entry(sound_speed)
	data["g"] = simple_entry(9.81)
	data["p_middle_factor"] = simple_entry(args.pressuremiddle_factor)

def get_number_of_timesteps(args, glp):
	time_interval = glp.scenario["time_interval"][1] - glp.scenario["time_interval"][0]
	time_interval_unit = glp.scenario["units"]["time_interval"]
	return math.ceil(convert_value_to_unit(glp, time_interval, time_interval_unit, "s") / convert_value_to_unit(glp, args.time_step, time_step_unit, "s"))

def add_time_grid(args, glp, data):
	number_of_timesteps = get_number_of_timesteps(args, glp)
	data["delta_t"] = simple_entry(convert_value_to_unit(glp, args.time_step, time_step_unit, "s"))
	data["t"] = simple_entry(range(0, number_of_timesteps + 1))
	data["t1"] = simple_entry(range(1, number_of_timesteps + 1))

def get_time_grid(args, glp):
	data = {}
	add_time_grid(args, glp, data)
	return data

def add_nodes(args, glp, block, data):
	nodes = []

	data["delta_in"] = {}
	data["delta_out"] = {}
	data["q_u_lb"] = {}
	data["q_u_ub"] = {}
	data["q_u_start"] = {}
	data["p_u_lb"] = {}
	data["p_u_ub"] = {}
	data["p_u_start"] = {}
	data["relaxation_arcs"] = {}

	for node_type in glp.node_types:
		node_type_data = []
		for node in block[node_type]:
			element = glp.get_element(node_type, node)
			nodes.append(node)
			node_type_data.append(node)
			set_node_delta_in_out(data, node)
			set_node_flow(glp, data, node, element)
			set_node_pressure(glp, data, node, element)
			set_node_relaxation_arcs(args, data, block, node)
		data[node_type] = simple_entry(node_type_data)

	data["nodes"] = simple_entry(nodes)

def set_node_delta_in_out(data, node):
	data["delta_in"][node] = []
	data["delta_out"][node] = []

def set_node_flow(glp, data, node, element):
	data["q_u_lb"][node] = get_value_in_unit(glp, element, "flowMin", "kg_per_s", default_value=0.0)
	data["q_u_ub"][node] = get_value_in_unit(glp, element, "flowMax", "kg_per_s", default_value=0.0)

def set_node_pressure(glp, data, node, element):
	data["p_u_lb"][node] = get_value_in_unit(glp, element, "pressureMin", "bar")
	data["p_u_ub"][node] = get_value_in_unit(glp, element, "pressureMax", "bar")

def set_node_relaxation_arcs(args, data, block, node):
	if args.relaxations:
		data["relaxation_arcs"][node] = []
		relaxation_strings = args.relaxations.split(",")
		for relaxation_string in relaxation_strings:
			node_arcs_list = relaxation_string.split(".")
			n = node_arcs_list.pop(0)
			if node == n:
				data["relaxation_arcs"][node] = [arc for arc in node_arcs_list if arc not in block["virtual_arcs"]]

def add_arcs(args, glp, block, data):
	arcs = []
	virtual_arcs = []
	x_num_max = 0

	data["delta_x"] = {}
	data["x_arc"] = {}
	data["x_arc_q"] = {}
	data["q_a_lb"] = {}
	data["q_a_ub"] = {}
	data["q_a_start"] = {}
	data["q_a_init"] = {}
	data["p_a_lb"] = {}
	data["p_a_ub"] = {}
	data["p_a_start"] = {}
	data["p_a_init"] = {}
	data["delta_p_cs_start"] = {}
	data["delta_p_cs_lb"] = {}
	data["delta_p_cs_ub"] = {}
	data["p_diff_max_valve"] = {}
	data["valve_open_start"] = {}
	data["D"] = {}
	data["A"] = {}
	data["slope"] = {}
	data["friction"] = {}

	for arc_type in glp.arc_types:
		arc_type_data = []
		for arc in block[arc_type]:
			element = glp.get_element(arc_type, arc)
			arcs.append(arc)
			arc_type_data.append(arc)
			set_arc_delta_in_out(data, arc, element)
			set_arc_flow(glp, data, arc, element)
			x_num = add_spatial_grid_arc(args, glp, data, arc, arc_type)
			x_num_max = max(x_num_max, x_num)
		data[arc_type] = simple_entry(arc_type_data)

	for arc in block["pipes"]:
		element = glp.pipes[arc]
		from_node_element = get_node_element(glp, element["from"])
		to_node_element = get_node_element(glp, element["to"])
		length = get_value_in_unit(glp, element, "length", "m")
		x_num = get_pipe_x_num(args, glp, arc)
		data["delta_x"][arc] = length / x_num
		data["p_a_lb"][arc] = get_value_in_unit(glp, element, "pressureMin", "bar", default_value=0.0)
		data["p_a_ub"][arc] = get_value_in_unit(glp, element, "pressureMax", "bar", default_value=1e3)
		data["D"][arc] = get_value_in_unit(glp, element, "diameter", "m")
		data["A"][arc] = math.pi * (data["D"][arc]**2) / 4
		data["slope"][arc] = (get_value_in_unit(glp, to_node_element, "height", "m", default_value=0.0) - get_value_in_unit(glp, from_node_element, "height", "m", default_value=0.0)) / length
		roughness = get_value_in_unit(glp, element, "roughness", "m")
		data["friction"][arc] = (2 * math.log10(data["D"][arc] / roughness) + 1.138)**(-2)
	for arc in block["short_pipes"]:
		element = glp.short_pipes[arc]
		set_arc_pressure_bounds_from_nodes(glp, data, arc, element)
	for arc in block["compressor_stations"]:
		element = glp.compressor_stations[arc]
		data["p_a_lb"][arc] = get_value_in_unit(glp, element, "pressureInMin", "bar")
		data["p_a_ub"][arc] = get_value_in_unit(glp, element, "pressureOutMax", "bar")
		data["delta_p_cs_ub"][arc] = data["p_a_ub"][arc] - data["p_a_lb"][arc]
		data["delta_p_cs_lb"][arc] = data["delta_p_cs_ub"][arc] / 10
	for arc in block["control_valves"]:
		element = glp.control_valves[arc]
		data["p_a_lb"][arc] = get_value_in_unit(glp, element, "pressureInMin", "bar")
		data["p_a_ub"][arc] = get_value_in_unit(glp, element, "pressureOutMax", "bar")
		data["delta_p_cs_lb"][arc] = get_value_in_unit(glp, element, "pressureDifferentialMin", "bar")
		data["delta_p_cs_ub"][arc] = get_value_in_unit(glp, element, "pressureDifferentialMax", "bar")
	for arc in block["valves"]:
		element = glp.valves[arc]
		set_arc_pressure_bounds_from_nodes(glp, data, arc, element)
		data["p_diff_max_valve"][arc] = get_value_in_unit(glp, element, "pressureDifferentialMax", "bar")
	for arc in block["virtual_arcs"]:
		arcs.append(arc)
		virtual_arcs.append(arc)
		arc_type, element = glp.get_arc_type_element(arc)
		from_node_connected, to_node_connected = set_arc_delta_in_out(data, arc, element)
		set_arc_flow(glp, data, arc, element)
		x_num = add_spatial_grid_arc(args, glp, data, arc, arc_type)
		x_num_max = max(x_num_max, x_num)
		fix_spatial_grid_virtual_arc(data["x_arc"], arc, from_node_connected, to_node_connected)
		fix_spatial_grid_virtual_arc(data["x_arc_q"], arc, from_node_connected, to_node_connected)
		data["p_a_lb"][arc] = get_value_in_unit(glp, element, "pressureInMin", "bar", default_value=0.0)
		data["p_a_ub"][arc] = get_value_in_unit(glp, element, "pressureOutMax", "bar", default_value=float('inf'))

	data["arcs"] = simple_entry(arcs)
	data["cs_cv"] = simple_entry(data["compressor_stations"][None] + data["control_valves"][None])
	data["virtual_arcs"] = simple_entry(virtual_arcs)
	data["x_num_max"] = simple_entry(x_num_max)

def set_arc_delta_in_out(data, arc, element):
	from_node = element["from"]
	to_node = element["to"]
	from_node_connected = False
	if from_node in data["nodes"][None]:
		data["delta_out"][from_node].append(arc)
		from_node_connected = True
	to_node_connected = False
	if to_node in data["nodes"][None]:
		data["delta_in"][to_node].append(arc)
		to_node_connected = True
	return (from_node_connected, to_node_connected)

def get_pipe_x_num(args, glp, arc):
	length = get_value_in_unit(glp, glp.pipes[arc], "length", "m")
	return math.ceil(length / args.spatial_step)

def add_spatial_grid_arc(args, glp, data, arc, arc_type):
	x_num = 1
	if arc_type == "pipes":
		x_num = get_pipe_x_num(args, glp, arc)
		data["x_arc"][arc] = list(range(0, x_num + 1))
		data["x_arc_q"][arc] = data["x_arc"][arc]
	elif arc_type == "short_pipes":
		data["x_arc"][arc] = [0]
		data["x_arc_q"][arc] = [0]
	else:
		data["x_arc"][arc] = [0, 1]
		data["x_arc_q"][arc] = [0]
	return x_num

def fix_spatial_grid_virtual_arc(grid, arc, from_node_connected, to_node_connected):
	if len(grid[arc]) > 1:
		if len(grid[arc]) > 2:
			grid[arc] = [grid[arc][0], grid[arc][-1]]
		if not to_node_connected:
			grid[arc].pop(1)
		if not from_node_connected:
			grid[arc].pop(0)

def set_arc_flow(glp, data, arc, element):
	data["q_a_lb"][arc] = get_value_in_unit(glp, element, "flowMin", "kg_per_s")
	data["q_a_ub"][arc] = get_value_in_unit(glp, element, "flowMax", "kg_per_s")

def set_arc_pressure_bounds_from_nodes(glp, data, arc, element):
	from_node_element = get_node_element(glp, element["from"])
	to_node_element = get_node_element(glp, element["to"])
	data["p_a_lb"][arc] = min(get_value_in_unit(glp, from_node_element, "pressureMin", "bar"), get_value_in_unit(glp, to_node_element, "pressureMin", "bar"))
	data["p_a_ub"][arc] = max(get_value_in_unit(glp, from_node_element, "pressureMax", "bar"), get_value_in_unit(glp, to_node_element, "pressureMax", "bar"))

def get_node_element(glp, node):
	if node in glp.entries:
		return glp.entries[node]
	if node in glp.exits:
		return glp.exits[node]
	if node in glp.innodes:
		return glp.innodes[node]

def set_inital_values_and_start_point(data, stationary_model):
	for node in data["nodes"][None]:
		data["q_u_start"][node] = stationary_model.q_u[0, node].value
		data["p_u_start"][node] = stationary_model.p_u[0, node].value
	for arc in data["arcs"][None]:
		for x in data["x_arc"][arc]:
			data["p_a_init"][x, arc] = stationary_model.p_a[x, 0, arc].value
			data["p_a_start"][x, arc] = data["p_a_init"][x, arc]
		for x in data["x_arc_q"][arc]:
			data["q_a_init"][x, arc] = stationary_model.q_a[x, 0, arc].value
			data["q_a_start"][x, arc] = data["q_a_init"][x, arc]
	for arc in data["compressor_stations"][None]:
		data["delta_p_cs_start"][arc] = max(0, stationary_model.delta_p_cs[0, arc].value)
	for arc in data["control_valves"][None]:
		data["delta_p_cs_start"][arc] = max(0, stationary_model.delta_p_cs[0, arc].value)
	for arc in data["valves"][None]:
		data["valve_open_start"][arc] = stationary_model.valve_open[0, arc].value

def set_stationary_start_point(data):
	for node in data["nodes"][None]:
		data["q_u_start"][node] = (data["q_u_lb"][node] + data["q_u_ub"][node]) / 2
		data["p_u_start"][node] = (data["p_u_lb"][node] + data["p_u_ub"][node]) / 2
	for arc in data["arcs"][None]:
		for x in data["x_arc_q"][arc]:
			data["q_a_start"][x, arc] = (data["q_a_lb"][arc] + data["q_a_ub"][arc]) / 2
		for x in data["x_arc"][arc]:
			data["p_a_start"][x, arc] = (data["p_a_lb"][arc] + data["p_a_ub"][arc]) / 2
	for arc in data["compressor_stations"][None]:
		data["delta_p_cs_start"][arc] = 0
	for arc in data["control_valves"][None]:
		data["delta_p_cs_start"][arc] = 0
	for arc in data["valves"][None]:
		data["valve_open_start"][arc] = 0

def set_tracking_parameters(args, data, tracking_model):
	data["q_u_tracking_factor"] = simple_entry(args.tracking_factor_q)
	data["p_u_tracking_factor"] = simple_entry(args.tracking_factor_p)
	data["q_u_tracking"] = {}
	data["p_u_tracking"] = {}
	for node in data["entries"][None] + data["exits"][None]:
		data["q_u_tracking"][node] = tracking_model.q_u[0, node].value
		data["p_u_tracking"][node] = tracking_model.p_u[0, node].value

def block_contains_nonlinearities(block):
	return len(block["pipes"]) > 0

def block_contains_integer_variables(args, block):
	if len(block["valves"]) > 0:
		return True
	if args.model_cs in ["MIP", "MIPo", "MIPa"]:
		if len(block["compressor_stations"]) > 0:
			return True
		if len(block["control_valves"]) > 0:
			return True
	return False

def get_block_mtype(args, block):
	contains_nonlinearities = block_contains_nonlinearities(block)
	contains_integer_variables = block_contains_integer_variables(args, block)
	if contains_nonlinearities:
		if contains_integer_variables:
			return "minlp"
		else:
			return "dnlp"
	else:
		if contains_integer_variables:
			return "miqcp"
		else:
			return "qcp"

def get_block_solver(args, block):
	contains_nonlinearities = block_contains_nonlinearities(block)
	contains_integer_variables = block_contains_integer_variables(args, block)
	if contains_nonlinearities:
		if contains_integer_variables:
			return args.solver_minlp
		else:
			return args.solver_nlp
	else:
		if contains_integer_variables:
			return args.solver_miqcp
		else:
			return args.solver_qcp

def add_args_to_glp(args, glp):
	glp.scenario["time_interval"][1] += convert_value_to_unit(glp, args.t_max_add, "h", glp.scenario["units"]["time_interval"])
	for node_type in ["exits", "innodes"]:
		nodes = glp.get_elements(node_type)
		for node in nodes:
			element = nodes[node]
			element["pressureMin"]["value"] = get_value_in_unit(glp, element, "pressureMin", "bar") + args.pressure_buffer
			element["pressureMin"]["unit"] = "bar"
			element["pressureMax"]["value"] = get_value_in_unit(glp, element, "pressureMax", "bar") - args.pressure_buffer
			element["pressureMax"]["unit"] = "bar"

def get_linear_interpolation_indices(point, points):
	if len(points) == 1:
		return (0, 0, 0)
	elif point <= points[0]:
		return (0, 1, 0)
	elif point >= points[-1]:
		return (len(points) - 2, len(points) - 1, 1)
	start_index = 0
	end_index = len(points) - 1
	while end_index - start_index >= 2:
		mid_index = int((end_index + start_index) / 2)
		if points[mid_index] <= point:
			start_index = mid_index
		else:
			end_index = mid_index
	weight = (point - points[start_index]) / (points[end_index] - points[start_index])
	return (start_index, end_index, weight)

def get_value_at_linear_interpolation_indices(linear_interpolation_indices, points, values):
	if len(values) == len(points):
		weight = linear_interpolation_indices[2]
		return (1 - weight) * values[linear_interpolation_indices[0]] + weight * values[linear_interpolation_indices[1]]
	elif len(values) == len(points) - 1:
		return values[linear_interpolation_indices[0]]
	else:
		raise Exception("Number of points and values does not match.")
