import matplotlib.pyplot as plt
from matplotlib.widgets import Slider, CheckButtons

time_factor = 1 / 60

entry_color = "#00FF00"
exit_color = "#FF0000"
innode_color = "#00FFFF"
pipe_color = "#000000"
compressor_station_color = "#FF0000"
valve_color = "#0000FF"
control_valve_color = "#FF00FF"
short_pipe_color = "#FFFF00"
markersize = 17

dist = {
	"left": 0.05,
	"right": 0.95,
	"bottom": 0.2,
	"top": 0.95
}
slider_width = 0.8
slider_height = 0.2
check_buttons_width = 0.1
check_buttons_height = 0.5

def draw_arcs(res, ax, arcs, color):
	for arc in arcs:
		element = res["edges"][arc]
		from_node = res["nodes"][element["from"]]
		to_node = res["nodes"][element["to"]]
		ax.plot([from_node["coordinates"][0], to_node["coordinates"][0]], [from_node["coordinates"][1], to_node["coordinates"][1]], linestyle="-", color=color)

def draw_nodes(res, ax, nodes, color):
	for node in nodes:
		element = res["nodes"][node]
		ax.plot(element["coordinates"][0], element["coordinates"][1], marker="o", color=color, markersize=markersize)
		ax.text(element["coordinates"][0], element["coordinates"][1], "\n" + node, horizontalalignment="center", verticalalignment="top")

def get_t_index(res, t):
	t_index = res["t"].index(t)
	if t_index < 0:
		min_diff = float("inf")
		for i in range(len(res["t"])):
			diff = abs(t - res["t"][i])
			if diff < min_diff:
				t_index = i
				min_diff = diff
	return t_index

def get_x_index(element, x):
	x_index = element["x"].index(x)
	if x_index < 0:
		min_diff = float("inf")
		for i in range(len(element["x"])):
			diff = abs(x - element["x"][i])
			if diff < min_diff:
				x_index = i
				min_diff = diff
	return x_index

def get_node_data(res, element, t, show_bounds):
	t_index = get_t_index(res, t)
	p = "p: " + str(round(element["pressure"][t_index], 1))
	q = "q: " + str(round(element["massflow"][t_index], 1))
	if show_bounds:
		p += " [" + str(round(element["pressure_lb"][t_index], 1)) + ", " + str(round(element["pressure_ub"][t_index], 1)) + "]"
		q += " [" + str(round(element["massflow_lb"][t_index], 1)) + ", " + str(round(element["massflow_ub"][t_index], 1)) + "]"
	return  p + "\n" + q

def get_compressor_station_data(res, element, t, show_bounds):
	t_index = get_t_index(res, t)
	delta_p =  "\u0394p: " + str(round(element["pressure_inc"][t_index], 1))
	q = "q: " + str(round(element["massflow"][t_index], 1))
	if show_bounds:
		delta_p += " [" + str(round(element["pressure_inc_lb"][t_index], 1)) + ", " + str(round(element["pressure_inc_ub"][t_index], 1)) + "]"
		q += " [" + str(round(element["massflow_lb"][t_index], 1)) + ", " + str(round(element["massflow_ub"][t_index], 1)) + "]"
	return delta_p + "\n" + q

def get_control_valve_data(res, element, t, show_bounds):
	t_index = get_t_index(res, t)
	delta_p =  "\u0394p: " + str(round(element["pressure_dec"][t_index], 1))
	q = "q: " + str(round(element["massflow"][t_index], 1))
	if show_bounds:
		delta_p += " [" + str(round(element["pressure_dec_lb"][t_index], 1)) + ", " + str(round(element["pressure_dec_ub"][t_index], 1)) + "]"
		q += " [" + str(round(element["massflow_lb"][t_index], 1)) + ", " + str(round(element["massflow_ub"][t_index], 1)) + "]"
	return delta_p + "\n" + q

def get_short_pipe_data(res, element, t, show_bounds):
	t_index = get_t_index(res, t)
	q = "q: " + str(round(element["massflow"][t_index], 1))
	if show_bounds:
		q += " [" + str(round(element["massflow_lb"][t_index], 1)) + ", " + str(round(element["massflow_ub"][t_index], 1)) + "]"
	return q

def get_valve_data(res, element, t, show_bounds):
	t_index = get_t_index(res, t)
	status = "Closed"
	if element["open_closed"][t_index] == 1:
		status = "Open"
	q = "q: " + str(round(element["massflow"][t_index], 1))
	if show_bounds:
		q += " [" + str(round(element["massflow_lb"][t_index], 1)) + ", " + str(round(element["massflow_ub"][t_index], 1)) + "]"
	return status + "\n" + q

def get_pipe_data(res, element, x, t):
	t_index = get_t_index(res, t)
	x_index = get_x_index(element, x)
	return "p: " + str(round(element["pressure"][t_index][x_index], 1)) + "\nq: " + str(round(element["massflow"][t_index][x_index], 1))

def plot(res):
	timestep_data = []

	delta_t = res["delta_t"] * time_factor
	t_max = max(res["t"]) * time_factor

	# plt.ion()
	fig, ax = plt.subplots()
	plt.subplots_adjust(left=dist["left"], right=dist["right"], bottom=dist["bottom"], top=dist["top"])
	ax.set_xticks([])
	ax.set_yticks([])

	# Draw network
	draw_arcs(res, ax, res["pipes"], pipe_color)
	draw_arcs(res, ax, res["short_pipes"], short_pipe_color)
	draw_arcs(res, ax, res["compressor_stations"], compressor_station_color)
	draw_arcs(res, ax, res["control_valves"], control_valve_color)
	draw_arcs(res, ax, res["valves"], valve_color)
	draw_nodes(res, ax, res["sources"], entry_color)
	draw_nodes(res, ax, res["sinks"], exit_color)
	draw_nodes(res, ax, res["innodes"], innode_color)

	# Create t slider
	ax_t = plt.axes([dist["left"] + ((dist["right"] - dist["left"]) * (1 - slider_width)), dist["bottom"] * (1 - slider_height) / 2, (dist["right"] - dist["left"]) * slider_width, dist["bottom"] * slider_height])
	slider_t = Slider(ax=ax_t, label="t (min)", valmin=0, valmax=t_max, valinit=0, valstep=delta_t, valfmt="%1.0f")

	# Create check buttons
	ax_check_buttons = plt.axes([dist["left"], dist["bottom"] * (1 - check_buttons_height) / 2, (dist["right"] - dist["left"]) * check_buttons_width, dist["bottom"] * check_buttons_height])
	check_buttons = CheckButtons(ax=ax_check_buttons, labels=["Pipes", "Bounds"])

	def update(t=None):
		if t is None:
			t = slider_t.val
		for text in timestep_data:
			text.remove()
		timestep_data.clear()

		show_pipe_data = check_buttons.get_status()[0]
		show_bounds = check_buttons.get_status()[1]
		for node in res["nodes"]:
			element = res["nodes"][node]
			timestep_data.append(ax.text(element["coordinates"][0], element["coordinates"][1], get_node_data(res, element, t / time_factor, show_bounds) + "\n", horizontalalignment="center", verticalalignment="baseline"))
		for arc in res["compressor_stations"]:
			element = res["edges"][arc]
			from_node = res["nodes"][element["from"]]
			to_node = res["nodes"][element["to"]]
			timestep_data.append(ax.text((from_node["coordinates"][0] + to_node["coordinates"][0]) / 2, (from_node["coordinates"][1] + to_node["coordinates"][1]) / 2, get_compressor_station_data(res, element, t / time_factor, show_bounds) + "\n", horizontalalignment="center", verticalalignment="baseline"))
		for arc in res["valves"]:
			element = res["edges"][arc]
			from_node = res["nodes"][element["from"]]
			to_node = res["nodes"][element["to"]]
			timestep_data.append(ax.text((from_node["coordinates"][0] + to_node["coordinates"][0]) / 2, (from_node["coordinates"][1] + to_node["coordinates"][1]) / 2, get_valve_data(res, element, t / time_factor, show_bounds) + "\n", horizontalalignment="center", verticalalignment="baseline"))
		for arc in res["control_valves"]:
			element = res["edges"][arc]
			from_node = res["nodes"][element["from"]]
			to_node = res["nodes"][element["to"]]
			timestep_data.append(ax.text((from_node["coordinates"][0] + to_node["coordinates"][0]) / 2, (from_node["coordinates"][1] + to_node["coordinates"][1]) / 2, get_control_valve_data(res, element, t / time_factor, show_bounds) + "\n", horizontalalignment="center", verticalalignment="baseline"))
		for arc in res["short_pipes"]:
			element = res["edges"][arc]
			from_node = res["nodes"][element["from"]]
			to_node = res["nodes"][element["to"]]
			timestep_data.append(ax.text((from_node["coordinates"][0] + to_node["coordinates"][0]) / 2, (from_node["coordinates"][1] + to_node["coordinates"][1]) / 2, get_short_pipe_data(res, element, t / time_factor, show_bounds) + "\n", horizontalalignment="center", verticalalignment="baseline"))
		if show_pipe_data:
			for arc in res["pipes"]:
				element = res["edges"][arc]
				delta_x = element["delta_x"]
				x_max = max(element["x"]) + 2 * delta_x
				from_node = res["nodes"][element["from"]]
				to_node = res["nodes"][element["to"]]
				for x in element["x"]:
					ratio = (x + delta_x) / x_max
					x_pos = from_node["coordinates"][0] * (1 - ratio) + to_node["coordinates"][0] * ratio
					y_pos = from_node["coordinates"][1] * (1 - ratio) + to_node["coordinates"][1] * ratio
					timestep_data.append(ax.plot(x_pos, y_pos, "r.")[0])
					timestep_data.append(ax.text(x_pos, y_pos, get_pipe_data(res, element, x, t / time_factor) + "\n", horizontalalignment="center"))
		fig.canvas.draw_idle()

	slider_t.on_changed(update)

	def update_check_buttons(id):
		update()

	check_buttons.on_clicked(update_check_buttons)

	update()
	return fig
