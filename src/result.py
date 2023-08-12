import data
from datetime import datetime
import json
import os

def get_list(set):
	return [e for e in set]

def get_node_data(stationary_model, model, node, element, type, ts):
	delta_t = model.delta_t.value
	data = {
		"in_edges": [arc for arc in model.delta_in[node]],
		"out_edges": [arc for arc in model.delta_out[node]],
		"type": type,
		"pressure": [],
		"pressure_lb": [],
		"pressure_ub": [],
		"massflow": [],
		"massflow_lb": [],
		"massflow_ub": [],
		"coordinates": [float(element["x"]), float(element["y"])]
	}
	for t in ts:
		if t == 0:
			m = stationary_model
		else:
			m = model
		p_u = m.p_u[t, node]
		q_u = m.q_u[t, node]
		data["pressure"].append(p_u.value)
		data["pressure_lb"].append(p_u.lb)
		data["pressure_ub"].append(p_u.ub)
		data["massflow"].append(q_u.value)
		data["massflow_lb"].append(q_u.lb)
		data["massflow_ub"].append(q_u.ub)

	return data

def get_arc_data(stationary_model, model, arc, element, singleFlow, ts):
	delta_t = model.delta_t.value
	delta_x = model.delta_x[arc]
	data = {
		"delta_x": delta_x,
		"x": [delta_x * x for x in model.x_arc[arc]],
		"pressure": [],
		"pressure_lb": [],
		"pressure_ub": [],
		"massflow": [],
		"massflow_lb": [],
		"massflow_ub": [],
		"from": element["from"],
		"to": element["to"],
		"single_flow": singleFlow
	}

	for t in ts:
		if t == 0:
			m = stationary_model
		else:
			m = model
		for key in ["pressure", "pressure_lb", "pressure_ub"]:
			data[key].append([])
		if singleFlow:
			data["massflow_lb"].append(m.q_a[0, t, arc].lb)
			data["massflow_ub"].append(m.q_a[0, t, arc].ub)
			data["massflow"].append(m.q_a[0, t, arc].value)
		else:
			for key in ["massflow", "massflow_lb", "massflow_ub"]:
				data[key].append([])
		for x in m.x_arc[arc]:
			p_a = m.p_a[x, t, arc]
			data["pressure"][-1].append(p_a.value)
			data["pressure_lb"][-1].append(p_a.lb)
			data["pressure_ub"][-1].append(p_a.ub)
			if not singleFlow:
				q_a = m.q_a[x, t, arc]
				data["massflow_lb"][-1].append(q_a.lb)
				data["massflow_ub"][-1].append(q_a.ub)
				data["massflow"][-1].append(q_a.value)

	return data

def get_pipe_data(stationary_model, model, arc, element, ts):
	data = get_arc_data(stationary_model, model, arc, element, False, ts)
	data["type"] = "pipe"
	data["diameter"] = model.D[arc]
	data["area"] = model.A[arc]
	data["friction"] = model.friction[arc]
	data["slope"] = model.slope[arc]
	return data

def get_compressor_station_data(stationary_model, model, arc, element, ts):
	delta_t = model.delta_t.value
	data = get_arc_data(stationary_model, model, arc, element, True, ts)
	data["type"] = "compressorStation"
	data["pressure_inc"] = []
	data["pressure_inc_lb"] = []
	data["pressure_inc_ub"] = []
	for t in ts:
		if t == 0:
			m = stationary_model
		else:
			m = model
		delta_p_cs = m.delta_p_cs[t, arc]
		data["pressure_inc"].append(delta_p_cs.value)
		data["pressure_inc_lb"].append(delta_p_cs.lb)
		data["pressure_inc_ub"].append(delta_p_cs.ub)
	return data

def get_control_valve_data(stationary_model, model, arc, element, ts):
	delta_t = model.delta_t.value
	data = get_arc_data(stationary_model, model, arc, element, True, ts)
	data["type"] = "controlValve"
	data["pressure_dec"] = []
	data["pressure_dec_lb"] = []
	data["pressure_dec_ub"] = []
	for t in ts:
		if t == 0:
			m = stationary_model
		else:
			m = model
		delta_p_cs = m.delta_p_cs[t, arc]
		data["pressure_dec"].append(delta_p_cs.value)
		data["pressure_dec_lb"].append(delta_p_cs.lb)
		data["pressure_dec_ub"].append(delta_p_cs.ub)
	return data

def get_short_pipe_data(stationary_model, model, arc, element, ts):
	data = get_arc_data(stationary_model, model, arc, element, True, ts)
	data["type"] = "shortPipe"
	return data

def get_valve_data(stationary_model, model, arc, element, ts):
	delta_t = model.delta_t.value
	data = get_arc_data(stationary_model, model, arc, element, True, ts)
	data["type"] = "valve"
	data["open_closed"] = []
	for t in ts:
		if t == 0:
			m = stationary_model
		else:
			m = model
		valve_open = m.valve_open[t, arc]
		data["open_closed"].append(int(valve_open.value))
	return data

def get_block_results(res, glp, stationary_model, model, ts):
	for node in model.entries:
		res["sources"].append(node)
		res["nodes"][node] = get_node_data(stationary_model, model, node, glp.entries[node], "source", ts)
	for node in model.exits:
		res["sinks"].append(node)
		res["nodes"][node] = get_node_data(stationary_model, model, node, glp.exits[node], "sink", ts)
	for node in model.innodes:
		res["innodes"].append(node)
		res["nodes"][node] = get_node_data(stationary_model, model, node, glp.innodes[node], "innode", ts)
	for arc in model.pipes:
		res["pipes"].append(arc)
		res["edges"][arc] = get_pipe_data(stationary_model, model, arc, glp.pipes[arc], ts)
	for arc in model.compressor_stations:
		res["compressor_stations"].append(arc)
		res["edges"][arc] = get_compressor_station_data(stationary_model, model, arc, glp.compressor_stations[arc], ts)
	for arc in model.control_valves:
		res["control_valves"].append(arc)
		res["edges"][arc] = get_control_valve_data(stationary_model, model, arc, glp.control_valves[arc], ts)
	for arc in model.short_pipes:
		res["short_pipes"].append(arc)
		res["edges"][arc] = get_short_pipe_data(stationary_model, model, arc, glp.short_pipes[arc], ts)
	for arc in model.valves:
		res["valves"].append(arc)
		res["edges"][arc] = get_valve_data(stationary_model, model, arc, glp.valves[arc], ts)

def get_cscost_value(model):
	weight = len(model.t1)
	value = 0
	for arc in model.compressor_stations:
		value += sum(model.delta_p_cs[t, arc].value for t in model.t1) / weight
	return value

def get_tracking_value(model):
	t = max(model.t1)
	value = 0
	if t != 0:
		for node in model.entries:
			value += model.q_u_tracking_factor * (model.q_u[t, node].value - model.q_u_tracking[node])**2
			value += model.p_u_tracking_factor * (model.p_u[t, node].value - model.p_u_tracking[node])**2
		for node in model.exits:
			value += model.q_u_tracking_factor * (model.q_u[t, node].value - model.q_u_tracking[node])**2
			value += model.p_u_tracking_factor * (model.p_u[t, node].value - model.p_u_tracking[node])**2
	return value

def get_pressuremiddle_value(model):
	weight = len(model.t1)
	value = 0
	for node in model.innodes:
		value += model.p_middle_factor * sum((model.p_u[t, node].value - (model.p_u[t, node].ub + model.p_u[t, node].lb) / 2)**2 for t in model.t1) / weight
	for node in model.exits:
		value += model.p_middle_factor * sum((model.p_u[t, node].value - (model.p_u[t, node].ub + model.p_u[t, node].lb) / 2)**2 for t in model.t1) / weight
	return value

def get_objective_value(args, blocks):
	value = 0
	for block in blocks:
		model = block.model
		if args.objective == "cscost":
			value += get_cscost_value(model)
		elif args.objective == "tracking":
			value += get_tracking_value(model)
		elif args.objective == "cscost_tracking":
			value += get_cscost_value(model) + get_tracking_value(model)
		elif args.objective == "pressuremiddle":
			value += get_pressuremiddle_value(model)
		elif args.objective == "cscost_pressuremiddle":
			value += get_cscost_value(model) + get_pressuremiddle_value(model)
		else:
			raise Exception("Unknown argument: " + arg)
	return value

def get_relaxation_p_q(blocks):
	relaxation_p = 0
	relaxation_q = 0
	for block in blocks:
		model = block.model
		if hasattr(model, "relaxation_arcs"):
			for node in model.nodes:
				for arc in model.relaxation_arcs[node]:
					for t in model.t1:
						relaxation_p = max(relaxation_p, abs(model.relaxation_p[t, node, arc].value))
						relaxation_q = max(relaxation_q, abs(model.relaxation_q[t, node, arc].value))
	return (relaxation_p, relaxation_q)

def get_results(args, glp, stationary_model, blocks, solving_time, piter, aiter, block_exectimes_list, print_errors, specific_errors):
	m = blocks[0].model
	delta_t = m.delta_t.value
	time_interval_start = data.convert_value_to_unit(glp, glp.scenario["time_interval"][0], glp.scenario["units"]["time_interval"], "s")
	time_interval_end = data.convert_value_to_unit(glp, glp.scenario["time_interval"][1], glp.scenario["units"]["time_interval"], "s") - data.convert_value_to_unit(glp, args.t_max_add, "h", "s")
	ts = [t for t in m.t if time_interval_start + delta_t * t <= time_interval_end]
	final_errors = {}
	for i in range(len(print_errors)):
		final_errors[print_errors[i]] = specific_errors[i]
	relaxation_p, relaxation_q = get_relaxation_p_q(blocks)

	res = {
		"network": glp.scenario["network"],
		"author": "A05",
		"version": "1.0",
		"date": datetime.today().strftime('%Y-%m-%d'),
		"models": {
			"pipe": args.model_pipe,
			"compressor_station": args.model_cs,
			"discr_time": args.discr_time,
			"discr_space_continuity": args.discr_space_continuity,
			"discr_space_momentum": args.discr_space_momentum
		},
		"data_type": "result",
		"pressure_at_grid_points": True,
		"massflow_at_grid_points": True,
		"sound_speed": m.c.value,
		# "bar2pascal_factor": m.bar2pascal_factor.value,
		"delta_t": delta_t,
		"t": [delta_t * t for t in ts],
		# "t1": [delta_t * t for t in m.t1],
		"nodes": {},
		"sources": [],
		"sinks": [],
		"innodes": [],
		"edges": {},
		"pipes": [],
		"compressor_stations": [],
		"control_valves": [],
		"short_pipes": [],
		"valves": [],
		"objective_value": get_objective_value(args, blocks),
		"solving_time": solving_time,
		"piter": piter,
		"aiter": aiter,
		"block_names": [block.name for block in blocks],
		"block_exectimes_list": block_exectimes_list,
		"final_errors": final_errors,
		"relaxation_p": relaxation_p,
		"relaxation_q": relaxation_q,
		"units": {
			"sound_speed": "m_per_s",
			# "bar2pascal_factor": "Pa_per_bar",
			"delta_t": "s",
			"t": "s",
			# "t1": "s",
			"delta_x": "m",
			"x": "m",
			"diameter": "m",
			"area": "m_square",
			"pressure_inc": "bar",
			"pressure_dec": "bar",
			"pressure": "bar",
			"massflow": "kg_per_s",
			"solving_time": "s"
		}
	}

	for block in blocks:
		get_block_results(res, glp, stationary_model, block.model, ts)

	return res

# Creates a string from the given number for the save file name
def get_num_string(num):
	num_string = str(num).replace(".", ",")
	if num_string.endswith(",0"):
		num_string = num_string[0:-2]
	return num_string

def save_results(res, args):
	input_file_name = os.path.splitext(os.path.basename(args.input_file))[0]
	search_string = "-inputdata"
	if input_file_name.lower().endswith(search_string):
		input_file_name = input_file_name[0:-len(search_string)]

	d = args.decomposition
	if d is None:
		d = ""
	save_file_name = input_file_name + "_" + args.objective + "_" + args.model_cs + "_" + d + "_" + get_num_string(args.spatial_step) + "_" + get_num_string(args.time_step) + ".json"

	working_dir = os.path.dirname(os.path.realpath(__file__))
	save_path = os.path.join(working_dir, "results", save_file_name)
	with open(save_path, 'w') as file:
		json_string = json.dump(res, file, indent=4)
		print("Saved results to " + save_path)
		return save_path
