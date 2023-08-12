from pyomo.environ import *
import model_cs
import model_objective
import model_pipe

def node_flow_bounds(model, t, node):
	return (model.q_u_lb[node], model.q_u_ub[node])

def node_flow_start(model, t, node):
	return model.q_u_start[node]

def node_pressure_bounds(model, t, node):
	return (model.p_u_lb[node], model.p_u_ub[node])

def node_pressure_start(model, t, node):
	return model.p_u_start[node]

def arc_flow_bounds(model, x, t, arc):
	if x not in model.x_arc_q[arc]:
		return (0, 0)
	if t not in model.t1:
		return (model.q_a_init[x, arc], model.q_a_init[x, arc])
	return (model.q_a_lb[arc], model.q_a_ub[arc])

def arc_flow_start(model, x, t, arc):
	if x not in model.x_arc_q[arc]:
		return 0
	if t not in model.t1:
		return model.q_a_init[x, arc]
	return model.q_a_start[x, arc]

def arc_pressure_bounds(model, x, t, arc):
	if x not in model.x_arc[arc]:
		return (0, 0)
	if t not in model.t1:
		return (model.p_a_init[x, arc], model.p_a_init[x, arc])
	return (model.p_a_lb[arc], model.p_a_ub[arc])

def arc_pressure_start(model, x, t, arc):
	if x not in model.x_arc[arc]:
		return 0
	if t not in model.t1:
		return model.p_a_init[x, arc]
	return model.p_a_start[x, arc]

def pressure_continuity(model, t, node, arc):
	if arc in model.delta_in[node]:
		if hasattr(model, "relaxation_arcs") and arc in model.relaxation_arcs[node]:
			return model.p_u[t, node] == model.p_a[max(model.x_arc[arc]), t, arc] + model.relaxation_p[t, node, arc]
		else:
			return model.p_u[t, node] == model.p_a[max(model.x_arc[arc]), t, arc]
	elif arc in model.delta_out[node]:
		if hasattr(model, "relaxation_arcs") and arc in model.relaxation_arcs[node]:
			return model.p_u[t, node] == model.p_a[0, t, arc] + model.relaxation_p[t, node, arc]
		else:
			return model.p_u[t, node] == model.p_a[0, t, arc]
	else:
		return Constraint.Skip

def mass_balance(model, t, node):
	q_in = 0
	q_out = 0
	if node in model.entries:
		q_in = model.q_u[t, node]
	elif node in model.exits:
		q_out = model.q_u[t, node]
	for arc in model.delta_in[node]:
		q_in = q_in + model.q_a[max(model.x_arc_q[arc]), t, arc]
		if hasattr(model, "relaxation_arcs") and arc in model.relaxation_arcs[node]:
			q_in = q_in + model.relaxation_q[t, node, arc]
	for arc in model.delta_out[node]:
		q_out = q_out + model.q_a[0, t, arc]
		if hasattr(model, "relaxation_arcs") and arc in model.relaxation_arcs[node]:
			q_out = q_out + model.relaxation_q[t, node, arc]
	return q_in == q_out

def valve_flow_lb(model, t, arc):
	return model.q_a[0, t, arc] >= model.valve_open[t, arc] * model.q_a_lb[arc]

def valve_flow_ub(model, t, arc):
	return model.q_a[0, t, arc] <= model.valve_open[t, arc] * model.q_a_ub[arc]

def valve_pressure_diff_lb(model, t, arc):
	return model.p_a[0, t, arc] - model.p_a[1, t, arc] >= - (1 - model.valve_open[t, arc]) * model.p_diff_max_valve[arc]

def valve_pressure_diff_ub(model, t, arc):
	return model.p_a[0, t, arc] - model.p_a[1, t, arc] <= (1 - model.valve_open[t, arc]) * model.p_diff_max_valve[arc]

def create_abstract_model(args):
	model = AbstractModel()

	# Parameters
	model.c = Param(within=PositiveReals) # Speed of sound in m/s
	model.g = Param(within=PositiveReals) # Gravitational acceleration
	model.bar2pascal_factor = Param(within=PositiveReals, default=1e5)

	# Time grid
	model.t = Set(within=NonNegativeIntegers) # Time grid
	model.t1 = Set(within=model.t) # Time grid without t=0
	model.delta_t = Param(within=PositiveReals, default=1) # Time step in s

	# Nodes
	model.nodes = Set()
	model.entries = Set(within=model.nodes)
	model.exits = Set(within=model.nodes)
	model.innodes = Set(within=model.nodes)

	# Node parameters
	model.q_u_lb = Param(model.nodes) # Node mass flow lower bound
	model.q_u_ub = Param(model.nodes) # Node mass flow upper bound
	model.q_u_start = Param(model.nodes) # Node mass flow starting point
	model.p_u_lb = Param(model.nodes) # Node pressure lower bound
	model.p_u_ub = Param(model.nodes) # Node pressure upper bound
	model.p_u_start = Param(model.nodes) # Node pressure starting point

	# Node variables
	model.q_u = Var(model.t1, model.nodes, bounds=node_flow_bounds, initialize=node_flow_start) # Node mass flow in kg/s
	model.p_u = Var(model.t1, model.nodes, bounds=node_pressure_bounds, initialize=node_pressure_start) # Node pressure in bar

	# Arcs
	model.arcs = Set()
	model.pipes = Set(within=model.arcs)
	model.short_pipes = Set(within=model.arcs)
	model.valves = Set(within=model.arcs)
	model.virtual_arcs = Set(within=model.arcs)
	model.cs_cv = Set(within=model.arcs)
	model.compressor_stations = Set(within=model.cs_cv)
	model.control_valves = Set(within=model.cs_cv)

	# Spatial grid
	model.x_num_max = Param(within=PositiveIntegers)
	model.x = RangeSet(0, model.x_num_max) # Spatial grid
	model.delta_x = Param(model.arcs, within=NonNegativeReals, default=0) # Spatial step in m
	model.x_arc = Set(model.arcs, within=model.x) # Arc spatial grid
	model.x_arc_q = Set(model.arcs, within=model.x) # Arc spatial grid for the massflow

	# Arc parameters
	model.delta_in = Set(model.nodes, within=model.arcs)
	model.delta_out = Set(model.nodes, within=model.arcs)
	model.q_a_lb = Param(model.arcs) # Arc mass flow lower bound
	model.q_a_ub = Param(model.arcs) # Arc mass flow upper bound
	model.q_a_start = Param(model.x, model.arcs) # Arc mass flow starting point
	model.q_a_init = Param(model.x, model.arcs) # Arc mass flow inital value
	model.p_a_lb = Param(model.arcs) # Arc pressure lower bound
	model.p_a_ub = Param(model.arcs) # Arc pressure upper bound
	model.p_a_start = Param(model.x, model.arcs) # Arc pressure starting point
	model.p_a_init = Param(model.x, model.arcs) # Arc pressure inital value

	# Arcs variables
	model.q_a = Var(model.x, model.t, model.arcs, bounds=arc_flow_bounds, initialize=arc_flow_start) # Arc mass flow in kg/s
	model.p_a = Var(model.x, model.t, model.arcs, bounds=arc_pressure_bounds, initialize=arc_pressure_start) # Arc pressure in bar

	if args.relaxations:
		model.relaxation_arcs = Set(model.nodes, within=model.arcs)
		model.relaxation_p = Var(model.t1, model.nodes, model.arcs, bounds=(-0.1, 0.1), initialize=0)
		model.relaxation_q = Var(model.t1, model.nodes, model.arcs, bounds=(-0.1, 0.1), initialize=0)

	# Valve parameters
	model.p_diff_max_valve = Param(model.valves, within=NonNegativeReals) # Maximal pressure difference between start and end of a valve

	# Valve variables
	model.valve_open = Var(model.t1, model.valves, within=Binary) # Indicator if the valve is open (1) or closed (0)

	# Constraints
	model.pressure_continuity = Constraint(model.t1, model.nodes, model.arcs, rule=pressure_continuity)
	model.mass_balance = Constraint(model.t1, model.nodes, rule=mass_balance)
	model.valve_flow_lb = Constraint(model.t1, model.valves, rule=valve_flow_lb)
	model.valve_flow_ub = Constraint(model.t1, model.valves, rule=valve_flow_ub)
	model.valve_pressure_diff_lb = Constraint(model.t1, model.valves, rule=valve_pressure_diff_lb)
	model.valve_pressure_diff_ub = Constraint(model.t1, model.valves, rule=valve_pressure_diff_ub)

	model_pipe.add_pipe_constraints(args, model)
	model_cs.add_cs_constraints(args, model)
	model_objective.add_objective(args, model)

	return model
