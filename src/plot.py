import matplotlib.pyplot as plt
import plot_network
import plot_node
import os


def plot(res, save_path):
	plot_node.plot(res).show()
	plot_network.plot(res)
	plt.show()
	# os.system("python3 Visualization/GUI.py \"" + save_path + "\"")
