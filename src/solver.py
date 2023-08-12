import multiprocessing
from pyomo.solvers.plugins.solvers.GAMS import GAMSShell
import time

# processes = max(int(multiprocessing.cpu_count() / 2), 2)
processes = max(int(multiprocessing.cpu_count()), 2)

def solve(model, mtype, solver, tee=False, time_limit=1000):
	starttime = time.time()
	G = GAMSShell()
	# res = G.solve(model, tee=tee, resLim=time_limit, tmpdir="./gams", logfile="output.log", load_solutions=True, keepfiles=True, report_timing=False, io_options={'mtype': mtype, "solver": solver, 'warmstart': True})
	res = G.solve(model, tee=tee, load_solutions=True, keepfiles=False, report_timing=False, io_options={'mtype': mtype, "solver": solver, 'warmstart': True, 'add_options': ["option ResLim=" + str(time_limit) + ";"]})
	if str(res.solver.termination_condition) not in ["locallyOptimal", "optimal", "feasible"]:
		raise Exception("Solver termination condition: " + str(res.solver.termination_condition))
	endtime = time.time()
	exectime = endtime - starttime
	return model, res, exectime

def solve_blocks_parallel(blocks, tee=False, time_limit=1000):
	pool = multiprocessing.Pool(processes)
	res = [pool.apply_async(solve, args=(block.model, block.mtype, block.solver, tee, time_limit)) for block in blocks]
	pool.close()
	pool.join()
	return [r.get() for r in res]
