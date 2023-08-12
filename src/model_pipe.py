from pyomo.environ import *

def continuity_equation_ISO2_impl_impl(model, x, t, arc):
	if x == 0 or x not in model.x_arc[arc]:
		return Constraint.Skip
	if t == 0:
		lhs = model.q_a[x, t, arc] - model.q_a[x - 1, t, arc]
	else:
		lhs = (model.bar2pascal_factor / model.delta_t) * (model.p_a[x, t, arc] - model.p_a[x, t - 1, arc])\
		+ ((model.c * model.c) / (model.A[arc] * model.delta_x[arc])) * (model.q_a[x, t, arc] - model.q_a[x - 1, t, arc])
	return lhs == 0

def continuity_equation_ISO2_impl_ibox(model, x, t, arc):
	if x == 0 or x not in model.x_arc[arc]:
		return Constraint.Skip
	if t == 0:
		lhs = model.q_a[x, t, arc] - model.q_a[x - 1, t, arc]
	else:
		lhs = (model.bar2pascal_factor / (2 * model.delta_t)) * (model.p_a[x, t, arc] - model.p_a[x, t - 1, arc] + model.p_a[x - 1, t, arc] - model.p_a[x - 1, t - 1, arc])\
		+ ((model.c * model.c) / (model.A[arc] * model.delta_x[arc])) * (model.q_a[x, t, arc] - model.q_a[x - 1, t, arc])
	return lhs == 0

def momentum_equation_ISO2_impl_impl(model, x, t, arc):
	if x == 0 or x not in model.x_arc[arc]:
		return Constraint.Skip
	if t == 0:
		lhs = (model.bar2pascal_factor * model.A[arc] / model.delta_x[arc]) * (model.p_a[x, t, arc] - model.p_a[x - 1, t, arc])
	else:
		lhs = (1 / model.delta_t) * (model.q_a[x, t, arc] - model.q_a[x, t - 1, arc])\
		+ (model.bar2pascal_factor * model.A[arc] / model.delta_x[arc]) * (model.p_a[x, t, arc] - model.p_a[x - 1, t, arc])
	rhs = ((- model.friction[arc] * model.c * model.c) / (2 * model.D[arc] * model.A[arc]))\
	* (model.q_a[x, t, arc] * abs(model.q_a[x, t, arc]) / (model.bar2pascal_factor * model.p_a[x, t, arc]))\
	- (model.g * model.A[arc] * model.slope[arc] * model.p_a[x, t, arc]) / (model.c * model.c)
	return lhs == rhs

def momentum_equation_ISO2_impl_ibox(model, x, t, arc):
	if x == 0 or x not in model.x_arc[arc]:
		return Constraint.Skip
	if t == 0:
		lhs = (model.bar2pascal_factor * model.A[arc] / model.delta_x[arc]) * (model.p_a[x, t, arc] - model.p_a[x - 1, t, arc])
	else:
		lhs = (1 / (2 * model.delta_t)) * (model.q_a[x, t, arc] - model.q_a[x, t - 1, arc] + model.q_a[x - 1, t, arc] - model.q_a[x - 1, t - 1, arc])\
		+ (model.bar2pascal_factor * model.A[arc] / model.delta_x[arc]) * (model.p_a[x, t, arc] - model.p_a[x - 1, t, arc])
	rhs = ((- model.friction[arc] * model.c * model.c) / (4 * model.D[arc] * model.A[arc]))\
	* (model.q_a[x, t, arc] * abs(model.q_a[x, t, arc]) / (model.bar2pascal_factor * model.p_a[x, t, arc]) + model.q_a[x - 1, t, arc] * abs(model.q_a[x - 1, t, arc]) / (model.bar2pascal_factor * model.p_a[x - 1, t, arc]))\
	- (model.g * model.A[arc] * model.slope[arc] * (model.p_a[x, t, arc] + model.p_a[x - 1, t, arc])) / (model.c * model.c)
	return lhs == rhs

def raise_unknown_arg(arg):
	raise Exception("Unknown argument: " + arg)

def add_pipe_constraints(args, model):
	# Pipe parameters
	model.D = Param(model.pipes, within=PositiveReals) # Diameter in m
	model.A = Param(model.pipes, within=PositiveReals) # Cross section area in m^2
	model.slope = Param(model.pipes) # Diameter in m
	model.friction = Param(model.pipes) # Friction factor

	# Pipe constraints
	if args.model_pipe == "ISO1":
		raise NotImplementedError()
	elif args.model_pipe == "ISO2":
		if args.discr_time == "impl_euler":
			if args.discr_space_continuity == "impl_euler":
				model.continuity_equation = Constraint(model.x, model.t1, model.pipes, rule=continuity_equation_ISO2_impl_impl)
			elif args.discr_space_continuity == "expl_euler":
				raise NotImplementedError()
			elif args.discr_space_continuity == "ibox":
				model.continuity_equation = Constraint(model.x, model.t1, model.pipes, rule=continuity_equation_ISO2_impl_ibox)
			else:
				raise_unknown_arg(args.discr_space_continuity)
			if args.discr_space_momentum == "impl_euler":
				model.momentum_equation = Constraint(model.x, model.t1, model.pipes, rule=momentum_equation_ISO2_impl_impl)
			elif args.discr_space_momentum == "expl_euler":
				raise NotImplementedError()
			elif args.discr_space_momentum == "ibox":
				model.momentum_equation = Constraint(model.x, model.t1, model.pipes, rule=momentum_equation_ISO2_impl_ibox)
			else:
				raise_unknown_arg(args.discr_space_momentum)
		elif args.discr_time == "expl_euler":
			raise NotImplementedError()
		else:
			raise_unknown_arg(args.discr_time)
	elif args.model_pipe == "ISO3":
		raise NotImplementedError()
	elif args.model_pipe == "ISO4":
		raise NotImplementedError()
	else:
		raise_unknown_arg(args.model_pipe)
