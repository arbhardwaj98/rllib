"""Interface for reward models."""

from abc import ABCMeta, abstractmethod

import torch.nn as nn


class AbstractReward(nn.Module, metaclass=ABCMeta):
    """Interface for Rewards of an Environment.

    A Reward is a model of the reward of the environment.

    Methods
    -------
    forward(state, action): Tensor, Union[Tensor, Tensor]
        return the next state distribution given a state and an action.

    """

    def __init__(self):
        super().__init__()

    @abstractmethod
    def forward(self, state, action, next_state):
        """Get reward distribution at current state and action."""
        raise NotImplementedError
