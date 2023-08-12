import argparse
from gaslib_parser import GasLibParser
import data
import decomposition
import initial_data
import model
import padm
import plot
import result
import scenario
import solver

if __name__ == '__main__':
	parser = argparse.ArgumentParser(description='Settings for PADM on GasLib')
	parser.add_argument('--input_file', '-i', metavar="INPUT FILE", help="Path to the input file", required=True)
	parser.add_argument('--time_step', '-t', metavar="TIMESTEP IN MINS", type=float, help="Length of a timestep in minutes", required=True)
	parser.add_argument('--spatial_step', '-x', metavar="SPATIAL STEP IN M", type=float, help="Length of a spatial step in meters", required=True)
	parser.add_argument('--model_pipe', metavar="MODEL FOR THE PIPES", help="The model used for the pipes (ISO1, ISO2, ISO3, ISO4)", default="ISO2")
	parser.add_argument('--model_cs', metavar="MODEL FOR THE COMPRESSOR STATIONS", help="The model used for compressor stations and control valves (LP, MIP)", default="LP")
	parser.add_argument('--discr_time', metavar="TIME DISCRETIZATION METHOD", help="The time discretization method used for the pipe model (impl_euler, expl_euler)", default="impl_euler")
	parser.add_argument('--discr_space_continuity', metavar="SPATIAL DISCRETIZATION FOR THE CONTINUITY EQUATION", help="The spatial discretization method used for the continuity equation (impl_euler, expl_euler, ibox)", default="impl_euler")
	parser.add_argument('--discr_space_momentum', metavar="SPATIAL DISCRETIZATION FOR THE MOMENTUM EQUATION", help="The spatial discretization method used for the momentum equation (impl_euler, expl_euler, ibox)", default="impl_euler")
	parser.add_argument('--solver_minlp', metavar="SOLVER USED FOR MINLPS", help="The solver that is used for MINLPs", default="knitro")
	parser.add_argument('--solver_nlp', metavar="SOLVER USED FOR NLPS", help="The solver that is used for NLPs", default="knitro")
	parser.add_argument('--solver_miqcp', metavar="SOLVER USED FOR MIPS", help="The solver that is used for MIPs", default="cplex")
	parser.add_argument('--solver_qcp', metavar="SOLVER USED FOR LPS", help="The solver that is used for LPs", default="cplex")
	parser.add_argument('--objective', '-o', metavar="OBJECTIVE FUNCTION TYPE", help="The objective function type (cscost, tracking, cscost_tracking, pressuremiddle, cscost_pressuremiddle)", default="cscost")
	parser.add_argument('--tracking_factor_q', metavar="TRACKING FACTOR FOR THE MASSFLOW", type=float, help="The tracking factor for the massflow if a tracking type objective function is used", default=1)
	parser.add_argument('--tracking_factor_p', metavar="TRACKING FACTOR FOR THE PRESSURE", type=float, help="The tracking factor for the pressure if a tracking type objective function is used", default=1)
	parser.add_argument('--pressuremiddle_factor', metavar="PRESSUREMIDDLE FACTOR", type=float, help="The tracking factor for the pressuremiddle tracking type objective function", default=1)
	parser.add_argument('--decomposition', '-d', metavar="NODE DECOMPOSITION", help="The nodes where the network is decomposed", default=None)
	parser.add_argument('--pressure_buffer', '-b', metavar="PRESSURE BUFFER IN BAR", type=float, help="A pressure buffer for the lower and upper pressure bounds of exits and innodes in bar", default=0)
	parser.add_argument('--t_max_add', metavar="ADDITIONAL TIME IN H", type=float, help="Additional time to add to the time horizon in h", default=0)
	parser.add_argument('--initial_data', metavar="INITIAL DATA FILE", help="Path to the initial data file", default=None)
	parser.add_argument('--time_limit', metavar="TIME LIMIT IN S", type=float, help="PADM time limit in s", default=1000)
	parser.add_argument('--relaxations', metavar="RELAXATIONS", help="Relaxations string", default="")
	args = parser.parse_args()

	print("Parse GasLib data...")
	glp = GasLibParser(args.input_file)
	glp.parse()
	data.add_args_to_glp(args, glp)

	print("Create abstract model...")
	abstract_model = model.create_abstract_model(args)

	if args.initial_data is None:
		print("Build stationary model...")
		stationary_model, mtype, solver_name = data.create_stationary_model_instance(args, glp, abstract_model)
		scenario.set_data(args, glp, stationary_model)
		print("Solve stationary model...")
		solver.solve(stationary_model, mtype, solver_name, time_limit=args.time_limit)
	else:
		print("Get inital data from file...")
		stationary_model = initial_data.get_initial_data(args, glp)

	tracking_model = None
	if "tracking" in args.objective:
		print("Build stationary tracking model...")
		tracking_model, mtype, solver_name = data.create_stationary_model_instance(args, glp, abstract_model)
		scenario.set_data(args, glp, tracking_model, tracking_model=True)
		print("Solve stationary tracking model...")
		solver.solve(tracking_model, mtype, solver_name, time_limit=args.time_limit)

	print("Create PADM blocks...")
	blocks = decomposition.get_blocks(glp, args)
	for block in blocks:
		instance, mtype, solver_name = data.create_model_instance(args, glp, abstract_model, block, stationary_model, tracking_model)
		scenario.set_data(args, glp, instance)
		decomposition.add_padm_block_data_to_block(args, block, instance, mtype, solver_name)
	decomposition.print_blocks_info(glp, blocks)
	linkvars = decomposition.add_linkvars_to_blocks(glp, blocks)
	padm_blocks = decomposition.get_padm_blocks(blocks)

	print_errors = ["p_a", "q_a"]
	print("Run PADM...")
	# solving_time, piter, aiter, block_exectimes_list, specific_errors = padm.padm(padm_blocks, linkvars, padm.default_parameters, print_errors=["p_a", "q_a"], plot_linkvars=["p_a", "q_a"], time_limit=args.time_limit)
	solving_time, piter, aiter, block_exectimes_list, specific_errors = padm.padm(padm_blocks, linkvars, padm.default_parameters, print_errors=print_errors, time_limit=args.time_limit)

	print("Get results...")
	res = result.get_results(args, glp, stationary_model, padm_blocks, solving_time, piter, aiter, block_exectimes_list, print_errors, specific_errors)

	print("Save results...")
	save_path = result.save_results(res, args)

	# print("Plot results...")
	# plot.plot(res, save_path)
