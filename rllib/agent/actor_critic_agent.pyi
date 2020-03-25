from typing import List

from torch.nn.modules.loss import _Loss
from torch.optim.optimizer import Optimizer

from rllib.algorithms.ac import ActorCritic
from rllib.dataset.datatypes import Observation
from rllib.policy import AbstractPolicy
from rllib.value_function import AbstractValueFunction
from .abstract_agent import AbstractAgent


class ActorCriticAgent(AbstractAgent):
    """Abstract Implementation of the Policy-Gradient Algorithm.

    The AbstractPolicyGradient algorithm implements the Policy-Gradient algorithm except
    for the computation of the rewards, which leads to different algorithms.

    TODO: build compatible function approximation.

    References
    ----------
    Williams, Ronald J. "Simple statistical gradient-following algorithms for
    connectionist reinforcement learning." Machine learning 8.3-4 (1992): 229-256.
    """
    trajectories: List[List[Observation]]
    actor_optimizer: Optimizer
    critic_optimizer: Optimizer
    actor_critic: ActorCritic
    target_update_freq: int
    num_rollouts: int
    eps: float = 1e-12

    def __init__(self, policy: AbstractPolicy, actor_optimizer: Optimizer,
                 critic: AbstractValueFunction, critic_optimizer: Optimizer,
                 criterion: _Loss, num_rollouts: int = 1, target_update_frequency: int = 1,
                 gamma: float = 1.0, exploration_steps: int = 0, exploration_episodes: int = 0) -> None: ...