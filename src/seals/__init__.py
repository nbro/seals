"""Benchmark environments for reward modeling and imitation."""

import gym

from seals import util
import seals.diagnostics  # noqa: F401
from seals.version import VERSION as __version__  # noqa: F401

# Classic control

gym.register(
    id="seals/CartPole-v0",
    entry_point="seals.classic_control:FixedHorizonCartPole",
    max_episode_steps=500,
)

gym.register(
    id="seals/MountainCar-v0",
    entry_point="seals.classic_control:mountain_car",
    max_episode_steps=200,
)

# MuJoCo

for env_base in ["Ant", "HalfCheetah", "Hopper", "Humanoid", "Swimmer", "Walker2d"]:
    gym.register(
        id=f"seals/{env_base}-v0",
        entry_point=f"seals.mujoco:{env_base}Env",
        max_episode_steps=util.get_gym_max_episode_steps(f"{env_base}-v3"),
    )
