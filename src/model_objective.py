from pyomo.environ import *

def get_cscost(model, obj):
	weight = len(model.t1)
	for arc in model.compressor_stations:
		obj += sum(model.delta_p_cs[t, arc] for t in model.t1) / weight
	return obj

def get_tracking(model, obj):
	t = max(model.t1)
	if t != 0:
		for node in model.entries:
			obj += model.q_u_tracking_factor * (model.q_u[t, node] - model.q_u_tracking[node])**2
			obj += model.p_u_tracking_factor * (model.p_u[t, node] - model.p_u_tracking[node])**2
		for node in model.exits:
			obj += model.q_u_tracking_factor * (model.q_u[t, node] - model.q_u_tracking[node])**2
			obj += model.p_u_tracking_factor * (model.p_u[t, node] - model.p_u_tracking[node])**2
	return obj

def get_pressuremiddle(model, obj):
	weight = len(model.t1)
	for node in model.innodes:
		obj += model.p_middle_factor * sum((model.p_u[t, node] - (model.p_u[t, node].ub + model.p_u[t, node].lb) / 2)**2 for t in model.t1) / weight
	for node in model.exits:
		obj += model.p_middle_factor * sum((model.p_u[t, node] - (model.p_u[t, node].ub + model.p_u[t, node].lb) / 2)**2 for t in model.t1) / weight
	return obj

def objective_cscost(model):
	return get_cscost(model, 0)

def objective_tracking(model):
	return get_tracking(model, 0)

def objective_cscost_tracking(model):
	obj = get_cscost(model, 0)
	return get_tracking(model, obj)

def objective_pressuremiddle(model):
	return get_pressuremiddle(model, 0)

def objective_cscost_pressuremiddle(model):
	obj = get_cscost(model, 0)
	return get_pressuremiddle(model, obj)

def raise_unknown_arg(arg):
	raise Exception("Unknown argument: " + arg)

def add_objective(args, model):
	# Tracking parameters
	if "tracking" in args.objective:
		model.q_u_tracking = Param(model.nodes) # Node mass flow tracking target
		model.p_u_tracking = Param(model.nodes) # Node pressure tracking target
		model.q_u_tracking_factor = Param() # Node mass flow tracking penalty factor
		model.p_u_tracking_factor = Param() # Node pressure tracking penalty factor
	if "pressuremiddle" in args.objective:
		model.p_middle_factor = Param() # Node pressure middle penalty factor

	# Objective
	if args.objective == "cscost":
		model.objective = Objective(rule=objective_cscost, sense=minimize)
	elif args.objective == "tracking":
		model.objective = Objective(rule=objective_tracking, sense=minimize)
	elif args.objective == "cscost_tracking":
		model.objective = Objective(rule=objective_cscost_tracking, sense=minimize)
	elif args.objective == "pressuremiddle":
		model.objective = Objective(rule=objective_pressuremiddle, sense=minimize)
	elif args.objective == "cscost_pressuremiddle":
		model.objective = Objective(rule=objective_cscost_pressuremiddle, sense=minimize)
	else:
		raise_unknown_arg(args.objective)
