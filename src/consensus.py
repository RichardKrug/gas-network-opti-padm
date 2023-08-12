
def get_consensus_problem(linkvars, param):
	if param["consensus"] == "mean":
		return consensus_mean(linkvars)
	elif param["consensus"] == "weighted_mean":
		return consensus_weighted_mean(linkvars)
	else:
		raise Exception("Unknown consensus method: " + str(param["consensus"]))

class consensus_mean:
	def __init__(self, linkvars):
		self.linkvars = linkvars

	def solve(self):
		for linkvar in self.linkvars:
			sum = 0
			for block in linkvar.blocks:
				sum += block.model.component(linkvar.name)[linkvar.index].value
			new_value = sum / len(linkvar.blocks)
			for block in linkvar.blocks:
				block.model.linkvar_target_value[linkvar.linkvar_index] = new_value

class consensus_weighted_mean:
	def __init__(self, linkvars):
		self.linkvars = linkvars

	def solve(self):
		for linkvar in self.linkvars:
			sum = 0
			weight_sum = 0
			for block in linkvar.blocks:
				model = block.model
				penalty_factor = max(model.slack_penalty_factor_pos[linkvar.linkvar_index].value, model.slack_penalty_factor_neg[linkvar.linkvar_index].value)
				sum += penalty_factor * model.component(linkvar.name)[linkvar.index].value
				weight_sum += penalty_factor
			new_value = sum / weight_sum
			for block in linkvar.blocks:
				block.model.linkvar_target_value[linkvar.linkvar_index] = new_value
