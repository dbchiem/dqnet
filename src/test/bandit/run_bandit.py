#!/usr/bin/env python

import os.path, sys
import argparse
sys.path.append(os.path.join(os.path.dirname(os.path.realpath(__file__)), os.pardir, os.pardir))
from bandit_environment import Environment
from agent import Agent
from network import Network
import numpy as np

############### Hyper-parameters ###############
Environment.EPOCH_COUNT = 10
Environment.FRAMES_SKIP = 1
Environment.FRAME_HEIGHT = 3
Environment.FRAME_WIDTH = 3
Environment.MAX_NO_OP = 0
Environment.MAX_REWARD = 0
Environment.ORIGINAL_HEIGHT = 3
Environment.ORIGINAL_WIDTH = 3
Environment.STEPS_PER_EPISODE = 100
Environment.STEPS_PER_EPOCH = 200

Agent.AGENT_HISTORY_LENGTH = 1
Agent.DISCOUNT_FACTOR = 0.99
Agent.FINAL_EXPLORATION = 0.1
Agent.FINAL_EXPLORATION_FRAME = 10000
Agent.INITIAL_EXPLORATION = 1.0
Agent.MINIBATCH_SIZE = 32
Agent.REPLAY_MEMORY_SIZE = 10000
Agent.REPLAY_START_SIZE = 100
Agent.TARGET_NETWORK_UPDATE_FREQUENCY = 100
Agent.UPDATE_FREQUENCY = 4
Agent.VALIDATION_SET_SIZE = 32 # MINIBATCH_SIZE <= VALIDATION_SET_SIZE <= REPLAY_START_SIZE * AGENT_HISTORY_LENGTH

Network.LEARNING_RATE = 0.0025
Network.MAX_DELTA = 0.0
Network.SCALE_FACTOR = 15.0
################################################

def get_arguments(argv):
	parser = argparse.ArgumentParser(description = 'Train/Evaluate deep Q-network')
	parser.add_argument('-e', '--evaluate-only', dest = 'evaluating', default = 0, type = int
		, help = 'Enable evaluating process (default: %(default)s)')
	parser.add_argument('-d', '--display-screen', dest = 'display_screen', default = 0, type = int
		, help = 'Display screen while evaluating')
	parser.add_argument('-f', '--file-network', dest = 'network_file', default = None
		, help = 'Network file to load from')
	return parser.parse_args(argv)

def main(argv):
	rng = np.random.RandomState(123)
	arg = get_arguments(argv)

	if arg.evaluating == 0:
		env = Environment(rng, one_state = False, display_screen = bool(arg.display_screen))
		agn = Agent(env.get_action_count(), Environment.FRAME_HEIGHT, Environment.FRAME_WIDTH, rng)
		env.train(agn)
		env.evaluate(agn, 10)
	elif arg.network_file is not None:
		env = Environment(rng, one_state = False, display_screen = bool(arg.display_screen))
		agn = Agent(env.get_action_count(), Environment.FRAME_HEIGHT, Environment.FRAME_WIDTH, rng, arg.network_file)
		env.evaluate(agn, 10)

if __name__ == '__main__':
	main(sys.argv[1:])