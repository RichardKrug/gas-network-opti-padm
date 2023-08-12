import padm
import gaslib_parser

def create_empty_block():
	block = {
		"nodes": [],
		"arcs": [],
		"virtual_arcs": []
	}
	for type in gaslib_parser.node_types + gaslib_parser.arc_types:
		block[type] = []
	return block

def create_node_block(node, type):
	block = create_empty_block()
	block["nodes"].append(node)
	block[type].append(node)
	return block

def create_arc_block(arc, type):
	block = create_empty_block()
	block["arcs"].append(arc)
	block[type].append(arc)
	return block

def get_node_blocks(glp):
	node_blocks = []

	for node_type, node in glp.get_all_nodes():
		node_blocks.append(create_node_block(node, node_type))

	return node_blocks

def get_not_decomposition_node_blocks(glp, decomposition_nodes):
	node_blocks = []

	for node_type, node in glp.get_all_nodes():
		if node not in decomposition_nodes:
			node_blocks.append(create_node_block(node, node_type))

	return node_blocks

def find_block_with_node(blocks, node):
	for block in blocks:
		if node in block["nodes"]:
			return block
	return None

def find_block_with_arc(blocks, arc_type, arc):
	for block in blocks:
		if arc in block[arc_type]:
			return block
	return None

def get_decomposition_nodes(decomposition_string):
	decomposition_nodes = {}
	node_strings = decomposition_string.split(",")
	for node_string in node_strings:
		node_arc_list = node_string.split(".")
		node = node_arc_list.pop(0)
		if node:
			decomposition_nodes[node] = node_arc_list
	return decomposition_nodes

def combine_blocks(block1, block2):
	for key in block1:
		block1[key].extend(block2[key])

def combine_blocks_by_arc(blocks, arc, element, type):
	from_node = element["from"]
	to_node = element["to"]
	block1 = find_block_with_node(blocks, from_node)
	if block1 is not None:
		block1["arcs"].append(arc)
		block1[type].append(arc)
	else:
		block1 = create_arc_block(arc, type)
		blocks.append(block1)
	if to_node in block1["nodes"]:
		return
	block2 = find_block_with_node(blocks, to_node)
	if block2 is not None:
		combine_blocks(block1, block2)
		blocks.remove(block2)

def get_active_passive_blocks(glp):
	blocks = get_node_blocks(glp)

	for arc_type in glp.passive_element_types:
		arcs = glp.get_elements(arc_type)
		for arc in arcs:
			element = arcs[arc]
			combine_blocks_by_arc(blocks, arc, element, arc_type)

	for arc_type in glp.active_element_types:
		for arc in glp.get_elements(arc_type):
			blocks.append(create_arc_block(arc, arc_type))

	return blocks

def get_node_decomposition_blocks(glp, decomposition_nodes):
	blocks = get_not_decomposition_node_blocks(glp, decomposition_nodes)

	for arc_type, arc, element in glp.get_all_arc_elements():
		combine_blocks_by_arc(blocks, arc, element, arc_type)

	for node in decomposition_nodes:
		decomposition_node_arcs = decomposition_nodes[node]
		type = glp.get_node_type(node)
		if decomposition_node_arcs:
			blocks_to_combine = []
			for block in blocks:
				is_block_connected = False
				is_block_to_combine = True
				for arc_type in glp.arc_types:
					for arc in block[arc_type]:
						if arc in decomposition_node_arcs:
							is_block_to_combine = False
							break
						element = glp.get_element(arc_type, arc)
						from_node = element["from"]
						to_node = element["to"]
						if node == from_node or node == to_node:
							is_block_connected = True
				if is_block_connected and is_block_to_combine:
					for other_node in block["nodes"]:
						if other_node in decomposition_node_arcs:
							is_block_to_combine = False
							break
				if is_block_connected and is_block_to_combine:
					blocks_to_combine.append(block)
			node_block = create_node_block(node, type)
			for block in blocks_to_combine:
				combine_blocks(node_block, block)
				blocks.remove(block)
			blocks.append(node_block)
		else:
			best_block_value = 0
			best_block = None
			for block in blocks:
				block_value = 0
				for arc_type in glp.arc_types:
					for arc in block[arc_type]:
						element = glp.get_element(arc_type, arc)
						from_node = element["from"]
						to_node = element["to"]
						if node == from_node or node == to_node:
							block_value += 1
				if block_value > best_block_value:
					best_block_value = block_value
					best_block = block
			if best_block is None:
				blocks.append(create_node_block(node, type))
			else:
				best_block["nodes"].append(node)
				best_block[type].append(node)

	return blocks

def get_block_name(block):
	if block["nodes"]:
		return block["nodes"][0]
	return block["arcs"][0]

def complete_blocks(glp, blocks):
	for block in blocks:
		block["name"] = get_block_name(block)
		for arc_type in glp.arc_types:
			for arc in block[arc_type]:
				element = glp.get_element(arc_type, arc)
				from_node = element["from"]
				to_node = element["to"]
				if from_node not in block["nodes"]:
					other_block = find_block_with_node(blocks, from_node)
					other_block["arcs"].append(arc)
					other_block["virtual_arcs"].append(arc)
				if to_node not in block["nodes"]:
					other_block = find_block_with_node(blocks, to_node)
					if arc not in other_block["virtual_arcs"]:
						other_block["arcs"].append(arc)
						other_block["virtual_arcs"].append(arc)

def get_blocks(glp, args):
	blocks = None
	if args.decomposition is None:
		blocks = get_active_passive_blocks(glp)
	else:
		decomposition_nodes = get_decomposition_nodes(args.decomposition)
		blocks = get_node_decomposition_blocks(glp, decomposition_nodes)

	complete_blocks(glp, blocks)

	return blocks

def print_blocks_info(glp, blocks):
	mtype_dict = {
		"qcp": "LP",
		"miqcp": "MIP",
		"dnlp": "NLP",
		"minlp": "MINLP"
	}
	print(str(len(blocks)) + " blocks")
	node_types = glp.node_types
	arc_types = glp.arc_types
	node_types = [node_type for node_type in node_types if max([len(block[node_type]) for block in blocks]) > 0]
	node_types = [node_type for node_type in node_types if node_type != "innodes"]
	arc_types = [arc_type for arc_type in arc_types if max([len(block[arc_type]) for block in blocks]) > 0]
	print("Block Nr. & \#nodes & \#" + " & \#".join(node_types) + " & \#" + " & \#".join(arc_types) + " & Type\\\\")
	block_number = 1
	for block in blocks:
		nodes = block["nodes"]
		arcs = block["arcs"]
		virtual_arcs = block["virtual_arcs"]

		numbers = [block_number, len(nodes)] + [len(block[node_type]) for node_type in node_types] + [len(block[arc_type]) for arc_type in arc_types]
		print(" & ".join(["$" + str(n) + "$" for n in numbers]) + " & " + mtype_dict[block["padm_block"].mtype] + "\\\\")
		block_number += 1

def add_padm_block_data_to_block(args, block, model, mtype, solver):
	block["padm_block"] = padm.block(model, mtype, solver, block["name"])

def create_linkvar(name, index, linkvar_index, block1, block2, start_penalty):
	linkvar = padm.linkvar(name, index, linkvar_index, [block1["padm_block"], block2["padm_block"]], start_penalty)
	block1["padm_block"].linkvars.append(linkvar)
	block2["padm_block"].linkvars.append(linkvar)
	return linkvar

def add_linkvars_to_blocks(glp, blocks):
	weight = len(blocks[0]["padm_block"].model.t1)
	start_penalty_flow = 1 / weight
	start_penalty_pressure = 1 / weight
	linkvars = []
	for block in blocks:
		for arc in block["virtual_arcs"]:
			arc_type, element = glp.get_arc_type_element(arc)
			other_block = find_block_with_arc(blocks, arc_type, arc)
			from_node = element["from"]
			to_node = element["to"]
			if from_node in block["nodes"]:
				for t in block["padm_block"].model.t:
					linkvars.append(create_linkvar("q_a", (0, t, arc), len(linkvars), block, other_block, start_penalty_flow))
					linkvars.append(create_linkvar("p_a", (0, t, arc), len(linkvars), block, other_block, start_penalty_pressure))
			if to_node in block["nodes"]:
				x_q = max(other_block["padm_block"].model.x_arc_q[arc])
				x_p = max(other_block["padm_block"].model.x_arc[arc])
				for t in block["padm_block"].model.t:
					linkvars.append(create_linkvar("q_a", (x_q, t, arc), len(linkvars), block, other_block, start_penalty_flow))
					linkvars.append(create_linkvar("p_a", (x_p, t, arc), len(linkvars), block, other_block, start_penalty_pressure))
	return linkvars

def get_padm_blocks(blocks):
	return [block["padm_block"] for block in blocks]
