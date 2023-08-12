from pyomo.environ import *

def compressor_station_pressure_bounds(model, t, arc):
	return (0, model.delta_p_cs_ub[arc])

def compressor_station_pressure_delta_start(model, t, arc):
	return model.delta_p_cs_start[arc]

def compressor_station_pressure_lp(model, t, arc):
	return model.p_a[0, t, arc] + model.delta_p_cs[t, arc] == model.p_a[1, t, arc]

def control_valve_pressure_lp(model, t, arc):
	return model.p_a[0, t, arc] - model.delta_p_cs[t, arc] == model.p_a[1, t, arc]

def compressor_station_flow_lb_mip(model, t, arc):
	return model.q_a[0, t, arc] >= model.cs_open[t, arc] * model.q_a_lb[arc]

def compressor_station_flow_ub_mip(model, t, arc):
	return model.q_a[0, t, arc] <= model.cs_open[t, arc] * model.q_a_ub[arc]

def compressor_station_pressure_diff_lb_mip(model, t, arc):
	return model.delta_p_cs[t, arc] >= model.cs_active[t, arc] * model.delta_p_cs_lb[arc]

def compressor_station_pressure_diff_ub_mip(model, t, arc):
	return model.delta_p_cs[t, arc] <= model.cs_active[t, arc] * (model.p_a_ub[arc] - model.p_a_lb[arc])

def compressor_station_pressure_lb_mip(model, t, arc):
	return model.p_a[0, t, arc] + model.delta_p_cs[t, arc] - model.p_a[1, t, arc] >= - (1 - model.cs_open[t, arc]) * (model.p_a_ub[arc] - model.p_a_lb[arc])

def compressor_station_pressure_ub_mip(model, t, arc):
	return model.p_a[0, t, arc] + model.delta_p_cs[t, arc] - model.p_a[1, t, arc] <= (1 - model.cs_open[t, arc]) * (model.p_a_ub[arc] - model.p_a_lb[arc])

def control_valve_pressure_lb_mip(model, t, arc):
	return model.p_a[0, t, arc] - model.delta_p_cs[t, arc] - model.p_a[1, t, arc] >= - (1 - model.cs_open[t, arc]) * (model.p_a_ub[arc] - model.p_a_lb[arc])

def control_valve_pressure_ub_mip(model, t, arc):
	return model.p_a[0, t, arc] - model.delta_p_cs[t, arc] - model.p_a[1, t, arc] <= (1 - model.cs_open[t, arc]) * (model.p_a_ub[arc] - model.p_a_lb[arc])

def compressor_station_active_mip(model, t, arc):
	return model.cs_active[t, arc] <= model.cs_open[t, arc]

def raise_unknown_arg(arg):
	raise Exception("Unknown argument: " + arg)

def add_cs_constraints(args, model):
	# Compressor station parameters
	model.delta_p_cs_start = Param(model.cs_cv, within=NonNegativeReals) # Compressor station pressure difference starting point
	model.delta_p_cs_ub = Param(model.cs_cv, within=NonNegativeReals) # Upper bound for the pressure difference in bar
	if args.model_cs == "MIP" or args.model_cs == "MIPa":
		model.delta_p_cs_lb = Param(model.cs_cv, within=NonNegativeReals) # Lower bound for the pressure difference in bar if the compressor station is active

	# Compressor station variables
	model.delta_p_cs = Var(model.t1, model.cs_cv, bounds=compressor_station_pressure_bounds, initialize=compressor_station_pressure_delta_start) # Compressor station pressure difference in bar
	if args.model_cs == "MIP" or args.model_cs == "MIPo":
		model.cs_open = Var(model.t1, model.cs_cv, within=Binary) # Indicator if the compressor station is open (1) or closed (0)
	if args.model_cs == "MIP" or args.model_cs == "MIPa":
		model.cs_active = Var(model.t1, model.cs_cv, within=Binary) # Indicator if the compressor station is active (1) or in bypass mode (0)

	# Compressor station constraints
	if args.model_cs == "LP" or args.model_cs == "MIPa":
		model.compressor_station_pressure = Constraint(model.t1, model.compressor_stations, rule=compressor_station_pressure_lp)
		model.control_valve_pressure = Constraint(model.t1, model.control_valves, rule=control_valve_pressure_lp)
	if args.model_cs == "MIP" or args.model_cs == "MIPo":
		model.compressor_station_pressure_lb = Constraint(model.t1, model.compressor_stations, rule=compressor_station_pressure_lb_mip)
		model.compressor_station_pressure_ub = Constraint(model.t1, model.compressor_stations, rule=compressor_station_pressure_ub_mip)
		model.control_valve_pressure_lb = Constraint(model.t1, model.control_valves, rule=control_valve_pressure_lb_mip)
		model.control_valve_pressure_ub = Constraint(model.t1, model.control_valves, rule=control_valve_pressure_ub_mip)
		model.compressor_station_flow_lb = Constraint(model.t1, model.cs_cv, rule=compressor_station_flow_lb_mip)
		model.compressor_station_flow_ub = Constraint(model.t1, model.cs_cv, rule=compressor_station_flow_ub_mip)
	if args.model_cs == "MIP" or args.model_cs == "MIPa":
		model.compressor_station_pressure_diff_lb = Constraint(model.t1, model.cs_cv, rule=compressor_station_pressure_diff_lb_mip)
		model.compressor_station_pressure_diff_ub = Constraint(model.t1, model.cs_cv, rule=compressor_station_pressure_diff_ub_mip)
	if args.model_cs == "MIP":
		model.compressor_station_active = Constraint(model.t1, model.cs_cv, rule=compressor_station_active_mip)

	if args.model_cs not in ["LP", "MIP", "MIPo", "MIPa"]:
		raise_unknown_arg(args.model_cs)
