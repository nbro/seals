"""Finite-horizon discrete environments with known transition dynamics."""

import abc
from typing import Optional

import gym
from gym import spaces
import numpy as np

from seals import util

class ResettableEnv(gym.Env, abc.ABC):
    """ABC for environments that are resettable.

    Specifically, these environments provide oracle access to sample from
    the initial state distribution and transition dynamics, and compute the
    reward and termination condition. Almost all simulated environments can
    meet these criteria."""

    def __init__(self):
        self._state_space = None
        self._action_space = None
        self.cur_state = None
        self._n_actions_taken = None
        self.seed()

    @abc.abstractmethod
    def initial_state(self):
        """Samples from the initial state distribution."""

    @abc.abstractmethod
    def transition(self, state, action):
        """Samples from transition distribution."""

    @abc.abstractmethod
    def reward(self, state, action, new_state):
        """Computes reward for a given transition."""

    @abc.abstractmethod
    def terminal(self, state, step: int) -> bool:
        """Is the state terminal?"""

    def obs_from_state(self, state):
        """Returns observation produced by a given state."""
        return state

    @property
    def state_space(self) -> gym.Space:
        """State space. Often same as observation_space, but differs in POMDPs."""
        return self._state_space

    @property
    def observation_space(self) -> gym.Space:
        """Observation space. Return type of reset() and component of step()."""
        return self.state_space

    @property
    def action_space(self) -> gym.Space:
        """Action space. Parameter type of step()."""
        return self._action_space

    @property
    def n_actions_taken(self) -> int:
        """Number of steps taken so far."""
        return self._n_actions_taken

    def seed(self, seed=None):
        if seed is None:
            # Gym API wants list of seeds to be returned for some reason, so
            # generate a seed explicitly in this case
            seed = np.random.randint(0, 1 << 31)
        self.rand_state = np.random.RandomState(seed)
        return [seed]

    def reset(self):
        self.cur_state = self.initial_state()
        self._n_actions_taken = 0
        return self.obs_from_state(self.cur_state)

    def step(self, action):
        if self.cur_state is None or self._n_actions_taken is None:
            raise ValueError("Need to call reset() before first step()")

        old_state = self.cur_state
        self.cur_state = self.transition(self.cur_state, action)
        obs = self.obs_from_state(self.cur_state)
        rew = self.reward(old_state, action, self.cur_state)
        done = self.terminal(self.cur_state, self._n_actions_taken)
        self._n_actions_taken += 1

        infos = {"old_state": old_state, "new_state": self.cur_state}
        return obs, rew, done, infos


class TabularModelEnv(ResettableEnv, abc.ABC):
    """ABC for tabular environments with known dynamics."""

    def __init__(
            self,
            *,
            transition_matrix : np.ndarray,
            reward_matrix : np.ndarray,
            horizon : float = np.inf,
            initial_state_dist : Optional[np.ndarray] = None,
    ):
        """Build tabular environment.

        Args:
                transition_matrix (np.ndarray, shape=(nS, nA, nS)):
                        Transition probabilities for a given state-action pair.
                reward_matrix (np.ndarray, len(shape) <= 3):
                        1-D, 2-D or 3-D array corresponding to rewards to a given `(state,
                        action, next_state)` triple.    A 2-D array assumes the `next_state`
                        is not used in the reward, and a 1-D array assumes neither the
                        `action` nor `next_state` are used.
                horizon (np.float):
                        Maximum number of timesteps, default `np.inf`.
                initial_state_dist (Optional[np.ndarray]):
                        Distribution from which state is sampled at the start of the episode.
                        If `None`, it is assumed initial state is always 0.
        """
        super().__init__()
        n_states, n_actions = transition_matrix.shape[:2]
        
        self.transition_matrix = transition_matrix
        self.reward_matrix = reward_matrix
        self.horizon = horizon

        if initial_state_dist is None:
                initial_state_dist = util.one_hot_encoding(0, n_states)
        self.initial_state_dist = initial_state_dist

        self._state_space = spaces.Discrete(n_states)
        self._action_space = spaces.Discrete(n_actions)

    def initial_state(self) -> int:
        return util.sample_distribution(
                self.initial_state_dist,
                random=self.rand_state,
        )

    def transition(self, state : int, action : int) -> int:
        return util.sample_distribution(
                self.transition_matrix[state, action],
                random=self.rand_state,
        )

    def reward(self, state : int, action : int, new_state : int) -> float:
        inputs = (state, action, new_state)[:len(self.reward_matrix.shape)]
        return self.reward_matrix[inputs]

    def terminal(self, state: int, n_actions_taken: int) -> bool:
        return n_actions_taken >= self.horizon
