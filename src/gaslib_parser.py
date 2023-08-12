import json
import os
import re
from xml.etree import ElementTree

node_types = ["entries", "exits", "innodes"]
arc_types = ["pipes", "short_pipes", "compressor_stations", "valves", "control_valves"]
active_element_types = ["compressor_stations", "valves", "control_valves"]
passive_element_types = ["pipes", "short_pipes"]

class GasLibParser(object):
	"""Class for parsing GasLib data."""

	def __init__(self, input_file):
		"""Constructor."""
		# dir_path = os.path.dirname(os.path.realpath(__file__))
		self.input_file = input_file
		self.gaslib_net_file = None
		# self.gaslib_net_file = os.path.join(dir_path, "instances", network, network + ".net")
		# self.gaslib_scn_file = os.path.join(dir_path, "instances", network, network + ".scn")
		self.namespaces = { "framework" : "http://gaslib.zib.de/Framework", "gas" : "http://gaslib.zib.de/Gas" }
		self.network = None
		self.entries = {}
		self.exits = {}
		self.innodes = {}
		self.pipes = {}
		self.compressor_stations = {}
		self.short_pipes = {}
		self.control_valves = {}
		self.valves = {}
		self.scenario = None
		self.node_types = node_types
		self.arc_types = arc_types
		self.active_element_types = active_element_types
		self.passive_element_types = passive_element_types

	def parse(self):
		"""Main parsing method."""
		self._parse_input_file()
		self._parse_net_file()
		# self._parse_scn_file()

	def _parse_input_file(self):
		with open(self.input_file, 'r') as file:
			self.scenario = json.load(file)
			self.gaslib_net_file = os.path.join(os.path.dirname(self.input_file), self.scenario["network"])

	def _parse_net_file(self):
		etree = ElementTree.parse(self.gaslib_net_file)
		self.network = etree.find(".//framework:title", self.namespaces).text
		nodes_element = etree.find("framework:nodes", self.namespaces)
		self._parse_nodes(nodes_element)
		connections_element = etree.find("framework:connections", self.namespaces)
		self._parse_connections(connections_element)

	def _parse_nodes(self, nodes_element):
		"""parse the nodes section"""
		sources_iter = nodes_element.iterfind("gas:source", self.namespaces)
		self._parse_elements(self.entries, sources_iter)
		sinks_iter = nodes_element.iterfind("gas:sink", self.namespaces)
		self._parse_elements(self.exits, sinks_iter)
		innodes_iter = nodes_element.iterfind("gas:innode", self.namespaces)
		self._parse_elements(self.innodes, innodes_iter)

	def _parse_connections(self, connections_element):
		"""parse the connections section"""
		pipes_iter = connections_element.iterfind("gas:pipe", self.namespaces)
		self._parse_elements(self.pipes, pipes_iter)
		short_pipes_iter = connections_element.iterfind("gas:shortPipe", self.namespaces)
		self._parse_elements(self.short_pipes, short_pipes_iter)
		compressors_iter = connections_element.iterfind("gas:compressorStation", self.namespaces)
		self._parse_elements(self.compressor_stations, compressors_iter)
		valve_iter = connections_element.iterfind("gas:valve", self.namespaces)
		self._parse_elements(self.valves, valve_iter)
		control_valves_iter = connections_element.iterfind("gas:controlValve", self.namespaces)
		self._parse_elements(self.control_valves, control_valves_iter)

	def _parse_elements(self, elements_dict, elements_iter):
		for element in elements_iter:
			element_dict = {}
			self._parse_element_attribs(element_dict, element)
			for child_element in element:
				child_element_dict = {}
				self._parse_element_attribs(child_element_dict, child_element)
				child_element_tag = self._strip_namespace(child_element)
				element_dict[child_element_tag] = child_element_dict
			elements_dict[element.get("id")] = element_dict

	def _parse_element_attribs(self, attribs_dict, element):
		for key in element.attrib:
			attribs_dict[key] = element.get(key)

	def _strip_namespace(self, element):
		tag = re.sub('[^}]*}(.*)', r'\1', element.tag)
		return tag

	def get_node_type(self, node):
		for node_type in self.node_types:
			if node in self.get_elements(node_type):
				return node_type
		raise Exception("Could not find node " + node)

	def get_arc_type(self, arc):
		for arc_type in self.arc_types:
			if arc in self.get_elements(arc_type):
				return arc_type
		raise Exception("Could not find arc " + arc)

	def get_elements(self, type):
		return getattr(self, type)

	def get_element(self, type, name):
		return self.get_elements(type)[name]

	def get_node_element(self, node):
		node_type = self.get_node_type(node)
		return self.get_element(node_type, node)

	def get_arc_element(self, arc):
		arc_type = self.get_arc_type(arc)
		return self.get_element(arc_type, arc)

	def get_node_type_element(self, node):
		node_type = self.get_node_type(node)
		return (node_type, self.get_element(node_type, node))

	def get_arc_type_element(self, arc):
		arc_type = self.get_arc_type(arc)
		return (arc_type, self.get_element(arc_type, arc))

	def get_all_nodes(self):
		result = []
		for node_type in self.node_types:
			nodes = self.get_elements(node_type)
			for node in nodes:
				result.append((node_type, node))
		return result

	def get_all_arcs(self):
		result = []
		for arc_type in self.arc_types:
			arcs = self.get_elements(arc_type)
			for arc in arcs:
				result.append((arc_type, arc))
		return result

	def get_all_node_elements(self):
		result = []
		for node_type in self.node_types:
			nodes = self.get_elements(node_type)
			for node in nodes:
				result.append((node_type, node, nodes[node]))
		return result

	def get_all_arc_elements(self):
		result = []
		for arc_type in self.arc_types:
			arcs = self.get_elements(arc_type)
			for arc in arcs:
				result.append((arc_type, arc, arcs[arc]))
		return result
