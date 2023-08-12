import json
import math
import data

class initialdata:
	def __init__(self):
		self.p_u = {}
		self.q_u = {}
		self.p_a = {}
		self.q_a = {}
		self.delta_p_cs = {}
		self.valve_open = {}
		self.x_arc = {}
		self.x_arc_q = {}

class variable:
	def __init__(self, value, lb, ub):
		self.value = value
		self.lb = lb
		self.ub = ub

def get_variable(glp, element, key, unit, unit_target, default_value=None):
	if key not in element and default_value is not None:
		return variable(default_value, default_value, default_value)
	value = data.convert_value_to_unit(glp, element[key][-1], unit, unit_target)
	if key + "_lb" in element:
		lb = data.convert_value_to_unit(glp, element[key + "_lb"][-1], unit, unit_target)
	else:
		lb = value
	if key + "_ub" in element:
		ub = data.convert_value_to_unit(glp, element[key + "_ub"][-1], unit, unit_target)
	else:
		ub = value
	return variable(value, lb, ub)

def get_spatial_variable(glp, element, key, unit, unit_target, x_index):
	value = data.convert_value_to_unit(glp, element[key][-1][x_index], unit, unit_target)
	if key + "_lb" in element:
		lb = data.convert_value_to_unit(glp, element[key + "_lb"][-1][x_index], unit, unit_target)
	else:
		lb = value
	if key + "_ub" in element:
		ub = data.convert_value_to_unit(glp, element[key + "_ub"][-1][x_index], unit, unit_target)
	else:
		ub = value
	return variable(value, lb, ub)

def get_linear_interpolation_variable(glp, element, key, unit, unit_target, linear_interpolation_indices):
	value = data.convert_value_to_unit(glp, data.get_value_at_linear_interpolation_indices(linear_interpolation_indices, element["x"], element[key][-1]), unit, unit_target)
	if key + "_lb" in element:
		lb = data.convert_value_to_unit(glp, data.get_value_at_linear_interpolation_indices(linear_interpolation_indices, element["x"], element[key + "_lb"][-1]), unit, unit_target)
	else:
		lb = value
	if key + "_ub" in element:
		ub = data.convert_value_to_unit(glp, data.get_value_at_linear_interpolation_indices(linear_interpolation_indices, element["x"], element[key + "_ub"][-1]), unit, unit_target)
	else:
		ub = value
	return variable(value, lb, ub)

def get_initial_data(args, glp):
	with open(args.initial_data, 'r') as file:
		initial_data_raw = json.load(file)
	initial_data = initialdata()
	for node in initial_data_raw["nodes"]:
		element = initial_data_raw["nodes"][node]
		initial_data.p_u[0, node] = get_variable(glp, element, "pressure", initial_data_raw["units"]["pressure"], "bar")
		initial_data.q_u[0, node] = get_variable(glp, element, "massflow", initial_data_raw["units"]["massflow"], "kg_per_s")
	for arc in initial_data_raw["edges"]:
		element = initial_data_raw["edges"][arc]
		if arc in initial_data_raw["pipes"]:
			length = data.get_value_in_unit(glp, glp.pipes[arc], "length", "m")
			x_num = math.ceil(length / args.spatial_step)
			initial_data.x_arc[arc] = list(range(0, x_num + 1))
			initial_data.x_arc_q[arc] = initial_data.x_arc[arc]
			delta_x = length / x_num
			for x_index in initial_data.x_arc[arc]:
				x = data.convert_value_to_unit(glp, x_index * delta_x, "m", initial_data_raw["units"]["x"])
				linear_interpolation_indices = data.get_linear_interpolation_indices(x, element["x"])
				initial_data.p_a[x_index, 0, arc] = get_linear_interpolation_variable(glp, element, "pressure", initial_data_raw["units"]["pressure"], "bar", linear_interpolation_indices)
				initial_data.q_a[x_index, 0, arc] = get_linear_interpolation_variable(glp, element, "massflow", initial_data_raw["units"]["massflow"], "kg_per_s", linear_interpolation_indices)
		elif "short_pipes" in initial_data_raw and arc in initial_data_raw["short_pipes"]:
			initial_data.x_arc[arc] = [0]
			initial_data.x_arc_q[arc] = [0]
			initial_data.p_a[0, 0, arc] = get_variable(glp, element, "pressure", initial_data_raw["units"]["pressure"], "bar")
			initial_data.q_a[0, 0, arc] = get_variable(glp, element, "massflow", initial_data_raw["units"]["massflow"], "kg_per_s")
		else:
			initial_data.x_arc[arc] = [0, 1]
			initial_data.x_arc_q[arc] = [0]
			for x_index in initial_data.x_arc[arc]:
				initial_data.p_a[x_index, 0, arc] = get_spatial_variable(glp, element, "pressure", initial_data_raw["units"]["pressure"], "bar", x_index)
			initial_data.q_a[0, 0, arc] = get_variable(glp, element, "massflow", initial_data_raw["units"]["massflow"], "kg_per_s")
	if "valves" in initial_data_raw:
		for arc in initial_data_raw["valves"]:
			element = initial_data_raw["edges"][arc]
			initial_data.valve_open[0, arc] = get_variable(glp, element, "open_closed", "", "", 0)
	if "compressor_stations" in initial_data_raw:
		for arc in initial_data_raw["compressor_stations"]:
			element = initial_data_raw["edges"][arc]
			initial_data.delta_p_cs[0, arc] = get_variable(glp, element, "pressure_inc", initial_data_raw["units"]["pressure_inc"], "bar", 0)
	if "control_valves" in initial_data_raw:
		for arc in initial_data_raw["control_valves"]:
			element = initial_data_raw["edges"][arc]
			initial_data.delta_p_cs[0, arc] = get_variable(glp, element, "pressure_dec", initial_data_raw["units"]["pressure_dec"], "bar", 0)

	return initial_data
