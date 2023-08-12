import data

# norm_density = 0.785

def get_t_in_unit(args, glp, model, t, tracking_model):
	unit_target = glp.scenario["units"]["timepoints"]
	time_interval_start = data.convert_value_to_unit(glp, glp.scenario["time_interval"][0], glp.scenario["units"]["time_interval"], unit_target)
	t_in_unit = data.convert_value_to_unit(glp, int(t) * model.delta_t.value, "s", unit_target) + time_interval_start
	if tracking_model:
		t_in_unit += data.convert_value_to_unit(glp, data.get_number_of_timesteps(args, glp) * model.delta_t.value, "s", unit_target)
	return t_in_unit

def fix_variable(variable, value):
	variable.setub(value)
	variable.setlb(value)

def fix_node_pressure(model, t, node, value):
	fix_variable(model.p_u[t, node], value)

def fix_arc_pressure(model, x, t, arc, value):
	fix_variable(model.p_a[x, t, arc], value)

def fix_node_massflow(model, t, node, value):
	fix_variable(model.q_u[t, node], value)

def fix_valve(model, t, arc, value):
	fix_variable(model.valve_open[t, arc], value)
	if value == 0:
		fix_variable(model.q_a[0, t, arc], value)

# def fix_node_volumeflow(model, t, node, value_in_1000m_cube_per_hour):
# 	value = norm_density * value_in_1000m_cube_per_hour * 1000 / (60 * 60)
# 	fix_node_massflow(model, t, node, value)

def fix_arc_pressures_at_node(model, t, node, value):
	for arc in model.delta_in[node]:
		fix_arc_pressure(model, max(model.x_arc[arc]), t, arc, value)
	for arc in model.delta_out[node]:
		fix_arc_pressure(model, 0, t, arc, value)

def set_node_data(args, glp, model, node, node_data, tracking_model):
	timepoints = node_data["timepoints"]
	for t in model.t1:
		t_in_unit = get_t_in_unit(args, glp, model, t, tracking_model)
		timepoints_indices = data.get_linear_interpolation_indices(t_in_unit, timepoints)
		if "massflow" in node_data and node_data["massflow"]:
			value = data.get_value_at_linear_interpolation_indices(timepoints_indices, timepoints, node_data["massflow"])
			value_in_unit = data.convert_value_to_unit(glp, value, glp.scenario["units"]["massflow"], "kg_per_s")
			fix_node_massflow(model, t, node, value_in_unit)
		if "pressure" in node_data and node_data["pressure"]:
			value = data.get_value_at_linear_interpolation_indices(timepoints_indices, timepoints, node_data["pressure"])
			value_in_unit = data.convert_value_to_unit(glp, value, glp.scenario["units"]["pressure"], "bar")
			fix_node_pressure(model, t, node, value_in_unit)
			fix_arc_pressures_at_node(model, t, node, value_in_unit)

def set_data(args, glp, model, tracking_model=False):
	if "sinks" in glp.scenario:
		for sink in glp.scenario["sinks"]:
			if sink in model.exits:
				set_node_data(args, glp, model, sink, glp.scenario["sinks"][sink], tracking_model)
	if "sources" in glp.scenario:
		for source in glp.scenario["sources"]:
			if source in model.entries:
				set_node_data(args, glp, model, source, glp.scenario["sources"][source], tracking_model)
	if "innodes" in glp.scenario:
		for innode in glp.scenario["innodes"]:
			if innode in model.innodes:
				set_node_data(args, glp, model, innode, glp.scenario["innodes"][innode], tracking_model)

	# Close all valves
	# for arc in model.valves:
	# 	for t in model.t1:
	# 		fix_valve(model, t, arc, 0)

	# Open all valves
	# for arc in model.valves:
	# 	for t in model.t1:
	# 		fix_valve(model, t, arc, 1)
