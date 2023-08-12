
def get_penalty_update_method(blocks, param):
	if param["penalty_update"] == "add":
		return penalty_update_add(blocks, param)
	elif param["penalty_update"] == "mult":
		return penalty_update_mult(blocks, param)
	elif param["penalty_update"] == "weighted_mult":
		return penalty_update_weighted_mult(blocks, param)
	elif param["penalty_update"] == "block_weighted_mult":
		return penalty_update_block_weighted_mult(blocks, param)
	elif param["penalty_update"] == "block_name_weighted_mult":
		return penalty_update_block_name_weighted_mult(blocks, param)
	else:
		raise Exception("Unknown penalty update method: " + str(param["penalty_update"]))

# Abstract class
class penalty_update:
	def __init__(self, blocks, param):
		self.blocks = blocks
		self.param = param

	def get_slacks_in_linkvars(self, model, linkvars):
		slacks = []
		for linkvar in linkvars:
			linkvar_index = linkvar.linkvar_index
			slacks.append((model.slack_penalty_factor_pos[linkvar_index], model.slack_pos[linkvar_index].value))
			slacks.append((model.slack_penalty_factor_neg[linkvar_index], model.slack_neg[linkvar_index].value))
		return slacks

	def get_slacks_in_block(self, block):
		return self.get_slacks_in_linkvars(block.model, block.linkvars)

	def get_slacks(self):
		slacks = []
		for block in self.blocks:
			slacks += self.get_slacks_in_block(block)
		return slacks

	def is_slack_active(self, slack):
		return slack[1] > self.param['slack_threshold']

	def get_active_slacks(self, slacks):
		return filter(lambda slack: self.is_slack_active(slack), slacks)

	def is_active_slacks_in_slacks(self, slacks):
		for slack in slacks:
			if self.is_slack_active(slack):
				return True
		return False

	def update_safe(self):
		self.update()
		slacks = self.get_slacks()
		for slack_penalty_factor, _ in slacks:
			if slack_penalty_factor.value > self.param['penalty_factor_max']:
				self.reset()
				return

	def reset(self):
		for block in self.blocks:
			model = block.model
			for linkvar in block.linkvars:
				linkvar_index = linkvar.linkvar_index
				# model.slack_penalty_factor_pos[linkvar_index].value = linkvar.start_penalty
				# model.slack_penalty_factor_neg[linkvar_index].value = linkvar.start_penalty
				model.slack_penalty_factor_pos[linkvar_index].value *= self.param['penalty_factor_rescale']
				model.slack_penalty_factor_neg[linkvar_index].value *= self.param['penalty_factor_rescale']

class penalty_update_add(penalty_update):
	def update(self):
		slacks = self.get_slacks()
		active_slacks = self.get_active_slacks(slacks)
		for slack_penalty_factor, slack_value in active_slacks:
			slack_penalty_factor.value += self.param['increment_penalty_summand']

class penalty_update_mult(penalty_update):
	def update(self):
		slacks = self.get_slacks()
		active_slacks = self.get_active_slacks(slacks)
		for slack_penalty_factor, slack_value in active_slacks:
			slack_penalty_factor.value *= self.param['increment_penalty_factor']

class penalty_update_weighted_mult(penalty_update):
	def update(self):
		slacks = self.get_slacks()
		slacks.sort(key=lambda element: element[1], reverse=True)
		slack_value_max = slacks[0][1]
		for slack_penalty_factor, slack_value in slacks:
			slack_penalty_factor.value *= (self.param['increment_penalty_factor_max'] - self.param['increment_penalty_factor_min']) * (slack_value / slack_value_max) + self.param['increment_penalty_factor_min']

class penalty_update_block_weighted_mult(penalty_update):
	def update(self):
		block_slacks_max = []
		for block in self.blocks:
			slacks = self.get_slacks_in_block(block)
			slacks.sort(key=lambda element: element[1], reverse=True)
			slack_value_max = slacks[0][1]
			block_slacks_max.append((slacks, slack_value_max))
		block_slacks_max.sort(key=lambda element: element[1], reverse=True)
		slack_value_max_max = block_slacks_max[0][1]
		for slacks, slack_value_max in block_slacks_max:
			increment_penalty_factor = (self.param['increment_penalty_factor_max'] - self.param['increment_penalty_factor_min']) * (slack_value_max / slack_value_max_max) + self.param['increment_penalty_factor_min']
			for slack_penalty_factor, _ in slacks:
				slack_penalty_factor.value *= increment_penalty_factor

class penalty_update_block_name_weighted_mult(penalty_update):
	def update(self):
		block_slacks_max = []
		for block in self.blocks:
			model = block.model
			block_name_slacks = {}
			for linkvar in block.linkvars:
				linkvar_index = linkvar.linkvar_index
				name = linkvar.name
				if name not in block_name_slacks:
					block_name_slacks[name] = []
				block_name_slacks[name].append((model.slack_penalty_factor_pos[linkvar_index], model.slack_pos[linkvar_index].value))
				block_name_slacks[name].append((model.slack_penalty_factor_neg[linkvar_index], model.slack_neg[linkvar_index].value))
			for name in block_name_slacks:
				slacks = block_name_slacks[name]
				slacks.sort(key=lambda element: element[1], reverse=True)
				slack_value_max = slacks[0][1]
				block_slacks_max.append((slacks, slack_value_max))
		block_slacks_max.sort(key=lambda element: element[1], reverse=True)
		slack_value_max_max = block_slacks_max[0][1]
		for slacks, slack_value_max in block_slacks_max:
			increment_penalty_factor = (self.param['increment_penalty_factor_max'] - self.param['increment_penalty_factor_min']) * (slack_value_max / slack_value_max_max) + self.param['increment_penalty_factor_min']
			for slack_penalty_factor, _ in slacks:
				slack_penalty_factor.value *= increment_penalty_factor
