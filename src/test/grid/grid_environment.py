import numpy as np
import cv2
import time
import os
import psutil
import gc
from grid_game import GridGame
from util.mem_convert import bytes2human

class Environment:
	"""docstring for Environment"""

	BUFFER_LEN = 1
	EPISODE_STEPS = 18000
	EPOCH_COUNT = 10
	EPOCH_STEPS = 10000
	EVAL_EPS = 0.001
	FRAMES_SKIP = 1
	FRAME_HEIGHT = 4
	FRAME_WIDTH = 4
	MAX_NO_OP = 0
	MAX_REWARD = 0

	def __init__(self, rng, one_state = False, display_screen = False):
		self.height = Environment.FRAME_HEIGHT
		self.width = Environment.FRAME_WIDTH
		self.api = GridGame(self.height, self.width, rng)
		self.rng = rng
		self.display_screen = display_screen
		self.minimal_actions = self.api.getMinimalActionSet()
		self.repeat = Environment.FRAMES_SKIP
		self.buffer_len = Environment.BUFFER_LEN
		self.eval_eps = Environment.EVAL_EPS
		
		self.merge_frame = np.zeros((self.buffer_len
								, self.height
								, self.width)
								, dtype = np.uint8)
		self.merge_id = 0
		self.max_reward = Environment.MAX_REWARD
		self.log_dir = ''
		self.network_dir = ''
		print self.minimal_actions

	def get_action_count(self):
		return len(self.minimal_actions)

	def train(self, agent, store_freq, folder = None, start_epoch = 0
			, ask_for_more = False):
		self._open_log_files(agent, folder)
		obs = np.zeros((self.height, self.width), dtype = np.uint8)
		epoch_count = Environment.EPOCH_COUNT

		self.need_reset = True
		epoch = start_epoch
		epoch_count = Environment.EPOCH_COUNT
		while epoch < epoch_count:
			steps_left = Environment.EPOCH_STEPS

			print "\n" + "=" * 50
			print "Epoch #%d" % (epoch + 1)
			episode = 0
			train_start = time.time()
			while steps_left > 0:
				num_step, _ = self._run_episode(agent, steps_left, obs)
				steps_left -= num_step
				episode += 1
				if steps_left == 0 or episode % 100 == 0:
					print "Finished episode #%d, steps_left = %d" \
						% (episode, steps_left)
			train_end = time.time()

			valid_values = agent.get_validate_values()
			eval_values = self.evaluate(agent)
			test_end = time.time()

			train_time = train_end - train_start
			test_time = test_end - train_end
			step_per_sec = Environment.EPOCH_STEPS * 1. / max(1, train_time)
			print "\tFinished epoch #%d, episode trained = %d\n" \
				"\tValidate values = %.3f, evaluate reward = %.3f\n"\
				"\tTrain time = %.0fs, test time = %.0fs, steps/sec = %.4f" \
					% (epoch + 1, episode, valid_values, eval_values\
						, train_time, test_time, step_per_sec)

			self._update_log_files(agent, epoch + 1, episode
								, valid_values, eval_values
								, train_time, test_time
								, step_per_sec, store_freq)
			gc.collect()
			epoch += 1
			if ask_for_more and epoch >= epoch_count:
				st = raw_input("\n***Enter number of epoch to continue training: ")
				more_epoch = 0
				try:
					more_epoch = int(st)
				except Exception, e:
					more_epoch = 0
				epoch_count += more_epoch

	def evaluate(self, agent, episodes = 30, obs = None):
		print "\n***Start evaluating"
		if obs is None:
			obs = np.zeros((self.height, self.width), dtype = np.uint8)
		sum_reward = 0.0
		sum_step = 0.0
		self.need_reset = True
		for episode in xrange(episodes):
			step, reward = self._run_episode(agent, 
				Environment.EPISODE_STEPS, obs, self.eval_eps, evaluating = True
				, print_Q = self.display_screen)
			sum_reward += reward
			sum_step += step
			print "Finished episode %d, reward = %d, step = %d" \
					% (episode + 1, reward, step)
		self.need_reset = True
		print "Average reward per episode = %.4f" \
				% (sum_reward / episodes)
		print "Average step per episode = %.4f" % (sum_step / episodes)
		return sum_reward / episodes

	def _prepare_game(self):
		if self.need_reset or self.api.game_over():
			self.api.reset_game()
			self.need_reset = False
			if Environment.MAX_NO_OP > 0:
				num_no_op = self.rng.randint(Environment.MAX_NO_OP + 1) \
							+ self.buffer_len
				for _ in xrange(num_no_op):
					self.api.act(0)

		for _ in xrange(self.buffer_len):
			self._update_buffer()

	def _run_episode(self, agent, steps_left, obs
					, eps = 0.0, evaluating = False, print_Q = False):
		self._prepare_game()

		start_lives = self.api.lives()
		step_count = 0
		sum_reward = 0
		is_terminal = False
		while step_count < steps_left and not is_terminal:
			self._get_screen(obs)
			action_id, is_random = agent.get_action(obs, eps, evaluating)
			
			reward = self._repeat_action(self.minimal_actions[action_id])
			reward_clip = reward
			if self.max_reward > 0:
				reward_clip = np.clip(reward, -self.max_reward, self.max_reward)

			if print_Q:
				print "Observation = \n", np.int32(obs) - self.api.translate
				print "Action%s = %d" % (" (random)" if is_random else ""
										, self.minimal_actions[action_id])
				print "Reward = %d" % (reward)
				raw_input()

			life_lost = not evaluating and self.api.lives() < start_lives
			is_terminal = self.api.game_over() or life_lost \
						or step_count + 1 >= steps_left

			agent.add_experience(obs, is_terminal, action_id, reward_clip
								, evaluating)
			sum_reward += reward
			step_count += 1
			
		return step_count, sum_reward

	def _update_buffer(self):
		self.api.getScreenGrayscale(self.merge_frame[self.merge_id, ...])
		self.merge_id = (self.merge_id + 1) % self.buffer_len

	def _repeat_action(self, action):
		reward = 0
		for i in xrange(self.repeat):
			reward += self.api.act(action)
			if i + self.buffer_len >= self.repeat:
				self._update_buffer()
		return reward

	def _get_screen(self, resized_frame):
		self._resize_frame(self.merge_frame.max(axis = 0), resized_frame)
				
	def _resize_frame(self, src_frame, dst_frame):
		cv2.resize(src = src_frame, dst = dst_frame,
					dsize = (self.width, self.height),
					interpolation = cv2.INTER_LINEAR)

	def _open_log_files(self, agent, folder):
		time_str = time.strftime("_%m-%d-%H-%M", time.localtime())
		base_rom_name = 'grid'

		if folder is not None:
			self.log_dir = folder
			self.network_dir = self.log_dir + '/network'
			return

		self.log_dir = '../run_results/grid/' + base_rom_name + time_str
		self.network_dir = self.log_dir + '/network'

		try:
			os.stat(self.log_dir)
		except OSError:
			os.makedirs(self.log_dir)

		try:
			os.stat(self.network_dir)
		except OSError:
			os.makedirs(self.network_dir)

		with open(self.log_dir + '/info.txt', 'w') as f:
			f.write(agent.get_info())
			f.write(self.api.game_info() + '\n\n')
			self._write_info(f, Environment)
			self._write_info(f, agent.__class__)
			self._write_info(f, agent.network.__class__)

		with open(self.log_dir + '/results.csv', 'w') as f:
			f.write("epoch,episode_train,validate_values,evaluate_reward"\
				",train_time,test_time,steps_per_second\n")

		mem = psutil.virtual_memory()
		with open(self.log_dir + '/memory.csv', 'w') as f:
			f.write("epoch,available,free,buffers,cached"\
					",available_readable,used_percent\n")
			f.write("%d,%d,%d,%d,%d,%s,%.1f\n" % \
					(0, mem.available, mem.free, mem.buffers, mem.cached
					, bytes2human(mem.available), mem.percent))

	def _update_log_files(self, agent, epoch, episode, valid_values
						, eval_values, train_time, test_time, step_per_sec
						, store_freq):
		print "Updating log files"
		with open(self.log_dir + '/results.csv', 'a') as f:
			f.write("%d,%d,%.4f,%.4f,%d,%d,%.4f\n" % \
						(epoch, episode, valid_values, eval_values
						, train_time, test_time, step_per_sec))

		mem = psutil.virtual_memory()
		with open(self.log_dir + '/memory.csv', 'a') as f:
			f.write("%d,%d,%d,%d,%d,%s,%.1f\n" % \
					(epoch, mem.available, mem.free, mem.buffers, mem.cached
					, bytes2human(mem.available), mem.percent))

		agent.dump_network(self.network_dir + ('/%03d' % (epoch)) + '.npz')

		if (store_freq >= 0 and epoch >= Environment.EPOCH_COUNT) or \
				(store_freq > 0 and (epoch % store_freq == 0)):
			agent.dump_exp(self.network_dir + '/exp.npz')

	def _write_info(self, f, c):
		hyper_params = [attr for attr in dir(c) \
			if not attr.startswith("__") and not callable(getattr(c, attr))]
		for param in hyper_params:
			f.write(str(c.__name__) + '.' + param + ' = ' + \
					str(getattr(c, param)) + '\n')
		f.write('\n')
