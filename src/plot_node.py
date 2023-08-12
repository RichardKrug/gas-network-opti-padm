import math
import matplotlib.pyplot as plt

color_pressure = "#0000FF"
color_flow_node = "#FF0000"
color_flow_arcs = "#FF00FF"
color_flow_all = "#00FF00"

def get_arc_flow(res, arc_name, position):
	if res["edges"][arc_name]["single_flow"]:
		return res["edges"][arc_name]["massflow"]
	return map(lambda a: a[position], res["edges"][arc_name]["massflow"])

def get_flow_in_arcs(res, node_name):
	flow_in_arcs = [0 for _ in res["t"]]
	for arc_name in res["nodes"][node_name]["in_edges"]:
		arc_flow = get_arc_flow(res, arc_name, -1)
		flow_in_arcs = map(lambda a, b: a + max(b, 0), flow_in_arcs, arc_flow)
	for arc_name in res["nodes"][node_name]["out_edges"]:
		arc_flow = get_arc_flow(res, arc_name, 0)
		flow_in_arcs = map(lambda a, b: a - min(b, 0), flow_in_arcs, arc_flow)
	return list(flow_in_arcs)

def get_flow_out_arcs(res, node_name):
	flow_out_arcs = [0 for _ in res["t"]]
	for arc_name in res["nodes"][node_name]["in_edges"]:
		arc_flow = get_arc_flow(res, arc_name, -1)
		flow_out_arcs = map(lambda a, b: a - min(b, 0), flow_out_arcs, arc_flow)
	for arc_name in res["nodes"][node_name]["out_edges"]:
		arc_flow = get_arc_flow(res, arc_name, 0)
		flow_out_arcs = map(lambda a, b: a + max(b, 0), flow_out_arcs, arc_flow)
	return list(flow_out_arcs)

def plot_line(ax, t, y, label, color):
	return ax.plot(t, y, '-', color=color, label=label)

def plot_pressure(res, node_name, ax):
	return plot_line(ax, res["t"], res["nodes"][node_name]["pressure"], "pressure", color_pressure)

def plot_flow_node(res, node_name, ax):
	return plot_line(ax, res["t"], res["nodes"][node_name]["massflow"], "massflow (node)", color_flow_node)

def plot_flow_in_arcs(res, node_name, ax):
	return plot_line(ax, res["t"], get_flow_in_arcs(res, node_name), "massflow (arcs)", color_flow_arcs)

def plot_flow_out_arcs(res, node_name, ax):
	return plot_line(ax, res["t"], get_flow_out_arcs(res, node_name), "massflow (arcs)", color_flow_arcs)

def plot_flow_in_all(res, node_name, ax):
	flow_in_all = list(map(lambda a, b: a + b, get_flow_in_arcs(res, node_name), res["nodes"][node_name]["massflow"]))
	return plot_line(ax, res["t"], flow_in_all, "massflow (all)", color_flow_all)

def plot_flow_out_all(res, node_name, ax):
	flow_out_all = list(map(lambda a, b: a + b, get_flow_out_arcs(res, node_name), res["nodes"][node_name]["massflow"]))
	return plot_line(ax, res["t"], flow_out_all, "massflow (all)", color_flow_all)

def add_node(res, node_name, ax):
	lines = plot_pressure(res, node_name, ax)
	ax.set_title(node_name)
	ax.set_xlabel("time (s)")
	ax.set_ylabel("pressure (bar)")
	ax_q = ax.twinx() # Flow plot uses same x axis
	if node_name in res["sources"]:
		lines += plot_flow_in_all(res, node_name, ax_q)
		lines += plot_flow_in_arcs(res, node_name, ax_q)
		lines += plot_flow_node(res, node_name, ax_q)
		ax_q.set_ylabel("massflow input (kg/s)")
	elif node_name in res["sinks"]:
		lines += plot_flow_out_all(res, node_name, ax_q)
		lines += plot_flow_out_arcs(res, node_name, ax_q)
		lines += plot_flow_node(res, node_name, ax_q)
		ax_q.set_ylabel("massflow output (kg/s)")
	else: # Innodes
		lines += plot_flow_in_all(res, node_name, ax_q)
		ax_q.set_ylabel("massflow throughput (kg/s)")
	labels = [line.get_label() for line in lines]
	ax_q.legend(lines, labels, loc=0)

def plot(res):
	node_names = res["sources"] + res["sinks"]# + res["innodes"]
	number_of_columns = math.ceil(math.sqrt(len(node_names)))
	number_of_rows = math.ceil(len(node_names) / number_of_columns)
	axes = []
	fig, axes_aux = plt.subplots(number_of_rows, number_of_columns)
	for row in axes_aux:
		for ax in row:
			axes.append(ax)
	for i in range(len(node_names)):
		add_node(res, node_names[i], axes[i])
	return fig
