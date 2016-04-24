import numpy as np
import cv2
from ale_python_interface import ALEInterface

class Environment:
	"""docstring for Environment"""

	STEPS_PER_EPOCH = 2000
	TRAIN_FRAMES_SKIP = 4
	EVAL_FRAMES_SKIP = 6

	ORIGINAL_HEIGHT = 210
	ORIGINAL_WIDTH = 160
	FRAME_HEIGHT = 8
	FRAME_WIDTH = 8

	def __init__(self, rom_name, display_screen = False):
		self.api = ALEInterface()
		self.api.setInt('random_seed', 123)
		self.api.setBool('display_screen', display_screen)
		self.rom_name = rom_name
		print '../rom/' + self.rom_name
		self.api.loadROM('../rom/' + self.rom_name)
		self.minimal_actions = self.api.getMinimalActionSet()
		self.merge_frame = np.zeros((2, Environment.ORIGINAL_HEIGHT, Environment.ORIGINAL_WIDTH), dtype = np.uint8)
		self.merge_id = 0
		print self.minimal_actions

	def get_action_count(self):
		return len(self.minimal_actions)

	def train(self, agent, epoch_count):
		obs = np.zeros((Environment.FRAME_HEIGHT, Environment.FRAME_WIDTH), dtype = np.uint8)
		for epoch in xrange(epoch_count):
			steps_left = Environment.STEPS_PER_EPOCH

			print "\n============================================"
			print "Epoch #%d" % epoch
			episode = 0
			while steps_left > 0:
				num_step, _ = self._run_episode(agent, steps_left, obs, Environment.TRAIN_FRAMES_SKIP)
				steps_left -= num_step
				if steps_left == 0 or episode % 1 == 0:
					print "Finished episode #%d, steps_left = %d" % (episode, steps_left)
				episode += 1
			avg_validate_values = agent.get_validate_values()
			print "Finsihed epoch #%d, average validate action values = %.3f" % (epoch, avg_validate_values)

		avg_reward = self.evaluate(agent, num_eval_episode = 1, obs = obs)
		print "Number of frame seen:", agent.num_train_obs
		print "Test average reward = %.3f" % (avg_reward)

	def evaluate(self, agent, num_eval_episode = 30, eps = 0.05, obs = None):
		print "\n***Start evaluating"
		if obs is None:
			obs = np.zeros((Environment.FRAME_HEIGHT, Environment.FRAME_WIDTH), dtype = np.uint8)
		sum_reward = 0.0
		for episode in xrange(num_eval_episode):
			_, reward = self._run_episode(agent, 18000, obs, Environment.EVAL_FRAMES_SKIP, eps, evaluating = True)
			sum_reward += reward
		return sum_reward / num_eval_episode

	def _run_episode(self, agent, steps_left, obs, repeat_action, eps = 0.0, evaluating = False):
		self.api.reset_game()		
		starting_lives = self.api.lives()
		is_terminal = False
		step_count = 0
		sum_reward = 0

		while step_count < steps_left and not is_terminal:
			self._get_screen(obs)
			action_id = agent.get_action(obs, eps, evaluating)
			
			reward = self._repeat_action(self.minimal_actions[action_id], repeat_action)
			is_terminal = self.api.game_over() or (self.api.lives() < starting_lives) or (step_count + 1 >= steps_left)
			agent.add_experience(obs, is_terminal, action_id, reward, evaluating)

			sum_reward += reward
			step_count += 1
		return step_count, sum_reward

	def _repeat_action(self, action, repeat_action):
		reward = 0
		for _ in xrange(repeat_action):
			reward += self.api.act(action)
		return reward

	def _get_screen(self, resized_frame):
		self.merge_id = (self.merge_id + 1) % 2
		self.api.getScreenGrayscale(self.merge_frame[self.merge_id, :])
		return self._resize_frame(self.merge_frame.max(axis = 0), resized_frame)
				
	def _resize_frame(self, src_frame, dst_frame):
		return cv2.resize(src = src_frame, dst = dst_frame,
						dsize = (Environment.FRAME_WIDTH, Environment.FRAME_HEIGHT), 
						interpolation = cv2.INTER_LINEAR)