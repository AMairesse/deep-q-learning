# -*- coding: utf-8 -*-
import random
import gymnasium as gym
import numpy as np
from collections import deque
from keras.models import Sequential
from keras.layers import Dense
from keras.optimizers import Adam
from keras import backend as K

import tensorflow as tf

EPISODES = 5

class DQNAgent:
    def __init__(self, state_size, action_size):
        self.state_size = state_size
        self.action_size = action_size
        self.memory = deque(maxlen=2000)
        self.gamma = 0.95    # discount rate
        self.epsilon = 1.0  # exploration rate
        self.epsilon_min = 0.01
        self.epsilon_decay = 0.99
        self.learning_rate = 0.001
        self.model = self._build_model()
        self.target_model = self._build_model()
        self.update_target_model()

    """Huber loss for Q Learning

    References: https://en.wikipedia.org/wiki/Huber_loss
                https://www.tensorflow.org/api_docs/python/tf/losses/huber_loss
    """

    def _huber_loss(self, y_true, y_pred, clip_delta=1.0):
        error = y_true - y_pred
        cond  = K.abs(error) <= clip_delta

        squared_loss = 0.5 * K.square(error)
        quadratic_loss = 0.5 * K.square(clip_delta) + clip_delta * (K.abs(error) - clip_delta)

        return K.mean(tf.where(cond, squared_loss, quadratic_loss))

    def _build_model(self):
        # Neural Net for Deep-Q learning Model
        model = Sequential()
        model.add(Dense(24, input_dim=self.state_size, activation='relu'))
        model.add(Dense(24, activation='relu'))
        model.add(Dense(self.action_size, activation='linear'))
        model.compile(loss=self._huber_loss,
                      optimizer=Adam(learning_rate=self.learning_rate))
        return model

    def update_target_model(self):
        # copy weights from model to target_model
        self.target_model.set_weights(self.model.get_weights())

    def memorize(self, state, action, reward, next_state, done):
        for i in range(state.shape[0]):
            self.memory.append((state[i], action[i], reward[i], next_state[i], done[i]))

    def act(self, state):
        if np.random.rand() <= self.epsilon:
            return [random.randrange(self.action_size) for _ in range(state.shape[0])]
        act_values = self.model.predict(state, verbose=0)
        return np.argmax(act_values, axis=1)  # returns action

    def replay(self, batch_size):
        minibatch = random.sample(self.memory, batch_size)
        for state, action, reward, next_state, done in minibatch:
            state = np.reshape(state, [1, state.shape[0]])
            next_state = np.reshape(next_state, [1, next_state.shape[0]])
            target = self.model.predict(state, verbose=0)
            if done:
                target[0][action] = reward
            else:
                t = self.target_model.predict(next_state, verbose=0)[0]
                target[0][action] = reward + self.gamma * np.amax(t)
            self.model.fit(state, target, epochs=1, verbose=0)
        if self.epsilon > self.epsilon_min:
            self.epsilon *= self.epsilon_decay

    def load(self, name):
        self.model.load_weights(name)

    def save(self, name):
        self.model.save_weights(name)


if __name__ == "__main__":
    NUM_ENVS = 32

    env = gym.vector.make('CartPole-v1', num_envs=NUM_ENVS)
    state_size = env.single_observation_space.shape[0]
    action_size = env.single_action_space.n
    agent = DQNAgent(state_size, action_size)
    # agent.load("./save/cartpole-ddqn.h5")
    done = False
    batch_size = 32

    for e in range(EPISODES):
        state, info = env.reset()
        state = np.reshape(state, [NUM_ENVS, state_size])
        for time in range(500):
            # env.render()
            action = agent.act(state)
            next_state, rewards, terminated, truncated, info = env.step(action)
            done = np.logical_or(terminated, truncated)
            rewards = [reward if not done[i] else -10 for i, reward in enumerate(rewards)]
            #x,x_dot,theta,theta_dot = next_state
            #r1 = (env.x_threshold - abs(x)) / env.x_threshold - 0.8
            #r2 = (env.theta_threshold_radians - abs(theta)) / env.theta_threshold_radians - 0.5
            #reward = r1 + r2            
            next_state = np.reshape(next_state, [NUM_ENVS, state_size])
            agent.memorize(state, action, rewards, next_state, done)
            state = next_state
            if done.any():
                agent.update_target_model()
                print("episode: {}/{}, score: {}, e: {:.2}"
                      .format(e, EPISODES, time, agent.epsilon))
                break
            if len(agent.memory) > batch_size:
                agent.replay(batch_size)
        # if e % 10 == 0:
        #     agent.save("./save/cartpole-ddqn.h5")