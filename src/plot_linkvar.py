import math
import matplotlib.pyplot as plt

linkvar_lists = None
fig = None
axes = None

linkvar_target_value_color = "#000000"
colors = ["#FF0000", "#00FF00", "#0000FF", "#FFFF00", "#FF00FF", "#00FFFF"]

def init(linkvars, linkvar_names):
	global linkvar_lists, fig, axes
	linkvar_lists = []
	axes = []
	for linkvar in linkvars:
		if linkvar.name in linkvar_names:
			add_to_linkvar_list(linkvar_lists, linkvar)
	add_block_colors(linkvar_lists)
	if not linkvar_lists:
		return
	number_of_columns = math.ceil(math.sqrt(len(linkvar_lists)))
	number_of_rows = math.ceil(len(linkvar_lists) / number_of_columns)
	fig, axes_aux = plt.subplots(number_of_rows, number_of_columns)
	# print("number_of_columns", number_of_columns)
	# print("number_of_rows", number_of_rows)
	if number_of_rows == 1:
		if number_of_columns == 1:
			axes.append(axes_aux)
		else:
			for ax in axes_aux:
				axes.append(ax)
	else:
		for row in axes_aux:
			for ax in row:
				axes.append(ax)
	plt.ion()
	plt.show()

def deinit():
	global linkvar_lists, fig, axes
	plt.ioff()
	plt.close(fig)
	linkvar_lists = None
	fig = None
	axes = None

def add_to_linkvar_list(linkvar_lists, linkvar):
	for linkvar_list in linkvar_lists:
		if fits_in_linkvar_list(linkvar_list, linkvar):
			linkvar_list.append(linkvar)
			return
	linkvar_lists.append([linkvar])

def fits_in_linkvar_list(linkvar_list, linkvar):
	l = linkvar_list[0]
	if linkvar.name != l.name or len(linkvar.blocks) != len(l.blocks):
		return False
	for block in linkvar.blocks:
		if block not in l.blocks:
			return False
	return True

def add_block_colors(linkvar_lists):
	color_index = 0
	for linkvar_list in linkvar_lists:
		for block in linkvar_list[0].blocks:
			if not hasattr(block, "color"):
				block.color = colors[color_index % len(colors)]
				color_index += 1

def plot_linkvars():
	if not linkvar_lists:
		return
	for i in range(len(linkvar_lists)):
		linkvar_list = linkvar_lists[i]
		ax = axes[i]

		# x axis
		x = range(len(linkvar_list))
		# Clear axis
		ax.cla()

		# Plot linkvar value for each block
		for block in linkvar_list[0].blocks:
			y = [block.model.component(linkvar.name)[linkvar.index].value for linkvar in linkvar_list]
			ax.plot(x, y, '-', color=block.color, label=block.name)

		# Plot linkvar target value
		y = [linkvar.blocks[0].model.linkvar_target_value[linkvar.linkvar_index].value for linkvar in linkvar_list]
		ax.plot(x, y, '-', color=linkvar_target_value_color)

		ax.legend()

		# Set title and labels
		ax.set_title(", ".join([block.name for block in linkvar_list[0].blocks]))
		ax.set_ylabel(linkvar_list[0].name)

	fig.canvas.draw_idle()
	plt.pause(0.001)
