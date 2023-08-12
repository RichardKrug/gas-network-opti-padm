#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pyomo.environ import *
import time
import consensus
import plot_linkvar
import penalty_update
import solver

default_parameters = {
	'increment_penalty_summand': 10,
	'increment_penalty_factor': 2,
	'increment_penalty_factor_max': 3,
	'increment_penalty_factor_min': 1,
	'max_ADM_loops': 5,
	'slack_threshold': 1e-1,
	'progress_threshold': 1e-2,
	'consensus': 'weighted_mean',
	'penalty_update': 'block_name_weighted_mult',
	'penalty_factor_max_factor': 1e9,
	'penalty_factor_rescale': 1e-6
}

linkvars_global = []

class linkvar:
	def __init__(self, name, index, linkvar_index, blocks, start_penalty=1):
		self.name = name
		self.index = index
		self.linkvar_index = linkvar_index
		self.blocks = blocks # blocks where this linking variable appears
		self.start_penalty = start_penalty

class block:
	def __init__(self, model, mtype, solver, name):
		self.model = model
		self.solver = solver
		self.mtype = mtype
		self.name = name
		self.linkvars = []

def get_linkvar_from_index(linkvars, linkvar_index):
	for linkvar in linkvars:
		if linkvar.linkvar_index == linkvar_index:
			return linkvar
	raise Exception("Could not find linkvar with index " + str(linkvar_index))

def get_linkvar_value(model, linkvar):
	return model.component(linkvar.name)[linkvar.index].value

def get_linkvar_value_from_index(model, linkvar_index, linkvars):
	linkvar = get_linkvar_from_index(linkvars, linkvar_index)
	return get_linkvar_value(model, linkvar)

def linkvar_target_value_init(model, linkvar_index):
	return get_linkvar_value_from_index(model, linkvar_index, linkvars_global)

def slack_penalty_factor_init(model, linkvar_index):
	return get_linkvar_from_index(linkvars_global, linkvar_index).start_penalty

def linkvar_slack_constraint(model, linkvar_index):
	linkvar = get_linkvar_from_index(linkvars_global, linkvar_index)
	return model.component(linkvar.name)[linkvar.index] + model.slack_pos[linkvar_index] - model.slack_neg[linkvar_index] == model.linkvar_target_value[linkvar_index]

def padm_objective(model):
	obj = model.objective.expr
	for linkvar_index in model.linkvar_indices:
		obj = obj + model.slack_penalty_factor_pos[linkvar_index] * model.slack_pos[linkvar_index] * model.slack_pos[linkvar_index] + model.slack_penalty_factor_neg[linkvar_index] * model.slack_neg[linkvar_index] * model.slack_neg[linkvar_index]
	return obj

def maximum_norm(list1, list2):
	return max([abs(a - b) for a, b in zip(list1, list2)])

def show(array):
	format_string ="{:>8} {:>8} {:>10} {:>14} {:>14} {:>14} {:>10}"
	for i in range(len(array) - 7):
		format_string += " {:>14}"
	print(format_string.format(*array))

def padm(blocks, linkvars, param, print_errors=[], plot_linkvars=[], time_limit=3600):
	global linkvars_global

	linkvars_global = linkvars

	if len(linkvars) > 0:
		param['penalty_factor_max'] = param['penalty_factor_max_factor'] * max([linkvar.start_penalty for linkvar in linkvars])
	consensus_problem = consensus.get_consensus_problem(linkvars, param)
	penalty_update_method = penalty_update.get_penalty_update_method(blocks, param)

	# Init linkvar plot
	if plot_linkvars:
		plot_linkvar.init(linkvars_global, plot_linkvars)
		# linkvars_output_dict = {}

	nslacks = 0
	# extend each block
	print('### extend models')
	for block in blocks:
		model = block.model

		linkvar_indices = [linkvar.linkvar_index for linkvar in block.linkvars]
		nslacks += len(linkvar_indices)
		model.linkvar_indices = Set(initialize=linkvar_indices)

		model.linkvar_target_value = Param(model.linkvar_indices, mutable=True, initialize=linkvar_target_value_init)
		model.slack_penalty_factor_pos = Param(model.linkvar_indices, mutable=True, initialize=slack_penalty_factor_init)
		model.slack_penalty_factor_neg = Param(model.linkvar_indices, mutable=True, initialize=slack_penalty_factor_init)

		model.slack_pos = Var(model.linkvar_indices, within=NonNegativeReals, initialize=0)
		model.slack_neg = Var(model.linkvar_indices, within=NonNegativeReals, initialize=0)

		model.linkvar_slack_constraint = Constraint(model.linkvar_indices, rule=linkvar_slack_constraint)

		model.objective.deactivate()
		model.padm_objective = Objective(rule=padm_objective, sense=minimize)

	print('### tighten linking variable bounds')
	for linkvar in linkvars:
		ub = min([block.model.component(linkvar.name)[linkvar.index].ub for block in linkvar.blocks if block.model.component(linkvar.name)[linkvar.index].ub is not None])
		lb = max([block.model.component(linkvar.name)[linkvar.index].lb for block in linkvar.blocks if block.model.component(linkvar.name)[linkvar.index].lb is not None])
		for block in linkvar.blocks:
			variable = block.model.component(linkvar.name)[linkvar.index]
			variable.setub(ub)
			variable.setlb(lb)

	print("Number of blocks: " + str(len(blocks)))
	print("Number of linking variables: " + str(len(linkvars)))
	print("Number of slacks: " + str(nslacks))

	block_exectimes_list = []

	startalltime = time.time()
	print('### starting padm using %d threads' % solver.processes)
	show(['piter', 'aiter', 'time', 'progress', 'max_penalty', 'max error', 'naslacks'] + list(map(lambda s: 'penalty_' + s, print_errors)) + list(map(lambda s: 'error_' + s, print_errors)))
	piter = 0
	nactiveslacks = nslacks + 1
	aiter_all = 0
	while nactiveslacks > 0:
		piter += 1
		aiter = 0
		progress = float("inf")
		linkvar_values = None

		while aiter < param['max_ADM_loops'] and param['progress_threshold'] < progress and nactiveslacks > 0:
			aiter += 1

			# Set all slacks to zero
			for block in blocks:
				model = block.model
				for linkvar in block.linkvars:
					linkvar_index = linkvar.linkvar_index
					model.slack_pos[linkvar_index].value = 0
					model.slack_neg[linkvar_index].value = 0

			# solve all blocks in parallel
			block_exectimes = []
			block_exectimes_list.append(block_exectimes)
			starttime = time.time()
			solve_results = solver.solve_blocks_parallel(blocks, time_limit=time_limit)
			for i in range(len(blocks)):
				model, res, block_exectime = solve_results[i]
				blocks[i].model = model
				block_exectimes.append(block_exectime)
				# print(res)
			# print(block_exectimes)

			# Plot linkvars
			if plot_linkvars:
				plot_linkvar.plot_linkvars()
				# for linkvar in linkvars:
				# 	for block in linkvar.blocks:
				# 		linkvar_output_name = linkvar.name + "_" + linkvar.index[2] + "_" + str(linkvar.index[0]) + "_" + block.name + "_" + str(piter) + "_" + str(aiter)
				# 		if linkvar_output_name not in linkvars_output_dict:
				# 			linkvars_output_dict[linkvar_output_name] = {}
				# 			# print(linkvar_output_name)
				# 		linkvars_output_dict[linkvar_output_name][linkvar.index[1]] = block.model.component(linkvar.name)[linkvar.index].value
				# 	linkvar_output_name = linkvar.name + "_" + linkvar.index[2] + "_" + str(linkvar.index[0]) + "_target_" + str(piter) + "_" + str(aiter)
				# 	if linkvar_output_name not in linkvars_output_dict:
				# 		linkvars_output_dict[linkvar_output_name] = {}
				# 		# print(linkvar_output_name)
				# 	linkvars_output_dict[linkvar_output_name][linkvar.index[1]] = linkvar.blocks[0].model.linkvar_target_value[linkvar.linkvar_index].value

			# get error, slack_penalty_factor_max, and new linkvar values
			error = 0
			slack_penalty_factor_max = 0
			linkvar_values_new = []

			# get specific errors and slack_penalty_factor_maxs
			specific_errors = []
			specific_slack_penalty_factor_maxs = []
			for print_error in print_errors:
				specific_errors.append(0)
				specific_slack_penalty_factor_maxs.append(0)
			for block in blocks:
				for linkvar in block.linkvars:
					linkvar_values_new.append(get_linkvar_value(block.model, linkvar))
					error = max(error, block.model.slack_pos[linkvar.linkvar_index].value, block.model.slack_neg[linkvar.linkvar_index].value)
					slack_penalty_factor_max = max(slack_penalty_factor_max, block.model.slack_penalty_factor_pos[linkvar.linkvar_index].value, block.model.slack_penalty_factor_neg[linkvar.linkvar_index].value)
					for i in range(len(print_errors)):
						if linkvar.name == print_errors[i]:
							specific_errors[i] = max(specific_errors[i], block.model.slack_pos[linkvar.linkvar_index].value, block.model.slack_neg[linkvar.linkvar_index].value)
							specific_slack_penalty_factor_maxs[i] = max(specific_slack_penalty_factor_maxs[i], block.model.slack_penalty_factor_pos[linkvar.linkvar_index].value, block.model.slack_penalty_factor_neg[linkvar.linkvar_index].value)

			# update progress
			if linkvar_values is not None:
				progress = maximum_norm(linkvar_values, linkvar_values_new)
			linkvar_values = linkvar_values_new

			# update nactiveslacks
			nactiveslacks = 0
			for linkvar in linkvars:
				for block in linkvar.blocks:
					model = block.model
					slack_pos_value = model.slack_pos[linkvar.linkvar_index].value
					slack_neg_value = model.slack_neg[linkvar.linkvar_index].value
					if slack_pos_value > param['slack_threshold'] or slack_neg_value > param['slack_threshold']:
						nactiveslacks += 1

			# solve consensus problem
			consensus_problem.solve()

			# reconstruct linking constraints with new right hand sides
			# for block in blocks:
			# 	block.model.linkvar_slack_constraint.reconstruct()

			endtime = time.time()
			exectime = endtime - starttime

			# Iteration output
			print_values = [piter, aiter, round(exectime, 2), round(progress, 6), round(slack_penalty_factor_max, 6), round(error, 6), nactiveslacks]
			for specific_slack_penalty_factor_max in specific_slack_penalty_factor_maxs:
				print_values.append(round(specific_slack_penalty_factor_max, 6))
			for specific_error in specific_errors:
				print_values.append(round(specific_error, 6))
			show(print_values)

			# Check time limit
			currtime = time.time()
			if nactiveslacks > 0 and currtime - startalltime >= time_limit:
				raise Exception("PADM time limit reached: " + str(time_limit))

		aiter_all += aiter

		# update penalty parameters in the objective function
		if nactiveslacks > 0:
			penalty_update_method.update_safe()
		# for block in blocks:
		# 	block.model.padm_objective.reconstruct()

	# Deinit linkvar plot
	if plot_linkvars:
		plot_linkvar.deinit()
		# linkvar_output_names = [key for key in linkvars_output_dict]
		# linkvar_output_names = []
		# for paiter in ["1_1", "2_1", "4_1", "6_1"]:
		# 	for block in ["CS02_N04_N05", "entry02", "N05", "target"]:
		# 		linkvar_output_names.append("q_a_CS02_N04_N05_0_" + block + "_" + paiter)
		# print("t " + " ".join(linkvar_output_names))
		# for t in range(25):
		# 	print(str(t) + " " + " ".join([str(linkvars_output_dict[linkvar_output_name][t]) for linkvar_output_name in linkvar_output_names]))
		# 	pass

	endalltime = time.time()
	solving_time = endalltime-startalltime
	print('### padm finished')
	print('### time %f sec' % solving_time)
	print('### piter: %d' % piter)
	print('### aiter: %d' % aiter_all)

	return (solving_time, piter, aiter_all, block_exectimes_list, specific_errors)
