import numpy as np
import time

class Experience:
	"""docstring for Experience"""
	def __init__(self, replay_mem_size, frame_height, frame_width, frames_per_state, rng):
		self.rng = rng
		self.replay_mem_size = replay_mem_size
		self.top = 0
		self.len = 0
		self.height = frame_height
		self.width = frame_width
		self.frames_per_state = frames_per_state
		self.obs = np.zeros((replay_mem_size, frame_height, frame_width), dtype = np.uint8)
		self.action = np.zeros((replay_mem_size, 1), dtype = np.uint8)
		self.reward = np.zeros((replay_mem_size, 1), dtype = np.int32)
		self.terminal = np.zeros((replay_mem_size, 1), dtype = np.bool_)
		self.return_state = np.zeros((frames_per_state, frame_height, frame_width), dtype = np.uint8)

	def add_experience(self, obs, is_terminal, action, reward):
		self.obs[self.top, :, :] = obs
		self.terminal[self.top] = is_terminal
		self.action[self.top] = action
		self.reward[self.top] = reward
		
		self.top = (self.top + 1) % self.replay_mem_size
		if self.len < self.replay_mem_size:
			self.len += 1

	def get_state(self, obs):
		assert self.len + 1 >= self.frames_per_state
		self.return_state[-1, :, :] = obs
		self.return_state[:-1, :, :] = self.obs.take(np.arange(self.top - self.frames_per_state + 1, self.top), axis = 0, mode = 'wrap')
		return self.return_state

	def get_random_minibatch(self, mbsize):
		assert self.len >= self.frames_per_state
		states = np.zeros((mbsize, self.frames_per_state + 1, self.height, self.width), dtype = np.uint8)
		action = np.zeros((mbsize, 1), dtype = np.uint8)
		reward = np.zeros((mbsize, 1), dtype = np.int32)
		terminal = np.zeros((mbsize, 1), dtype = np.bool_)

		cnt = 0
		while cnt < mbsize:
			start_id = self.rng.randint(1, self.len - self.frames_per_state + 1, mbsize - cnt) + self.top * (self.len >= self.replay_mem_size)
			end_id = start_id + self.frames_per_state - 1
			not_terminal = [not np.any(self.terminal.take(np.arange(i - 1, j - 1), axis = 0, mode = 'wrap')) 
								for i, j in zip(start_id, end_id)]
			num_ok = np.sum(not_terminal)								
			ids = np.asarray([range(start_id[i] - 1, end_id[i] + 1) for i, j in enumerate(not_terminal) if j == True], dtype = np.int32)
			
			states[cnt : cnt + num_ok, ...] = self.obs.take(ids.ravel(), axis = 0, mode = 'wrap')\
							.reshape(num_ok, self.frames_per_state + 1, self.height, self.width)
			tmp = self.action.take(end_id[not_terminal] - 1, mode = 'wrap')
			action[cnt : cnt + num_ok] = self.action.take(end_id[not_terminal] - 1, mode = 'wrap').reshape(-1, 1)
			reward[cnt : cnt + num_ok] = self.reward.take(end_id[not_terminal] - 1, mode = 'wrap').reshape(-1, 1)
			terminal[cnt : cnt + num_ok] = self.terminal.take(end_id[not_terminal] - 1, mode = 'wrap').reshape(-1, 1)
			cnt += np.sum(num_ok)
		return (states, action, reward, terminal)

def trivial_test():
	np.random.seed(123)
	height = 2
	width = 3
	replay_mem_size = 5
	frames_per_state = 2
	exp = Experience(replay_mem_size, height, width, frames_per_state)
	for i in xrange(8):
		obs = (i + 1) * np.ones((height, width), dtype = np.uint8)
		action = np.random.randint(4)
		reward = np.random.randint(10) * (2 * np.random.randint(2) - 1)
		terminal = (np.random.randint(5) == 0)

		exp.update_current_observation(obs, terminal)
		exp.add_action_reward(action, reward)

		print "After iteration #%d\nExp #%d:" % (i, i)
		#print exp.get_last_experience()
		print exp.obs, exp.action, exp.reward, exp.terminal

	for i in xrange(5):
		print "Get minibatch %i" % i
		print exp.get_random_minibatch(2)

def max_len_test():
	np.random.seed(123)
	height = 84
	width = 84
	frames_per_state = 10
	replay_mem_size1 = 10
	replay_mem_size2 = 100
	exp1 = Experience(replay_mem_size1, height, width, frames_per_state)
	exp2 = Experience(replay_mem_size2, height, width, frames_per_state)
	for i in xrange(20):
		obs = np.uint8(np.random.randint(0, 256, (height, width)))
		action = np.random.randint(8)
		reward = np.random.randint(10) * (2 * np.random.randint(2) - 1)
		terminal = (np.random.randint(10) == 0)

		exp1.update_current_observation(obs, terminal)
		exp1.add_action_reward(action, reward)

		exp2.update_current_observation(obs, terminal)
		exp2.add_action_reward(action, reward)

	obs = exp2.obs.take(np.arange(exp2.top - replay_mem_size1, exp2.top), axis = 0, mode = 'wrap')
	action = exp2.action.take(np.arange(exp2.top - replay_mem_size1, exp2.top), mode = 'wrap').reshape(-1, 1)
	reward = exp2.reward.take(np.arange(exp2.top - replay_mem_size1, exp2.top), mode = 'wrap').reshape(-1, 1)
	terminal = exp2.terminal.take(np.arange(exp2.top - replay_mem_size1, exp2.top), mode = 'wrap').reshape(-1, 1)

	print "obs equal", np.allclose(exp1.obs, obs)
	print "action equal", np.allclose(exp1.action, action)
	print "reward equal", np.allclose(exp1.reward, reward)
	print "terminal equal", np.allclose(exp1.terminal, terminal)

def speed_test():
	np.random.seed(123)
	height = 84
	width = 84
	frames_per_state = 4
	replay_mem_size = 1000
	exp = Experience(replay_mem_size, height, width, frames_per_state)
	start_time = time.time()
	n = 50000
	for i in xrange(n):
		obs = np.uint8(np.random.randint(0, 256, (height, width)))
		action = np.random.randint(8)
		reward = np.random.randint(10) * (2 * np.random.randint(2) - 1)
		terminal = (np.random.randint(10) == 0)

		exp.update_current_observation(obs, terminal)
		exp.add_action_reward(action, reward)
		if i % (n / 10) == 0:
			print "Done %d%%" % (i * 100 / n)

	elapsed = time.time() - start_time
	print "Per update", elapsed / n

	m = 10000
	start_time = time.time()
	for i in xrange(m):
		a, b, c, d, e = exp.get_random_minibatch(32)
		if i % (m / 10) == 0:
			print "Done %d%%" % (i * 100 / m)
	elapsed = time.time() - start_time
	print "Per access", elapsed / n

def main():
	speed_test()

if __name__ == '__main__':
	main()