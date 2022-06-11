"""Implementation of a Transformation that scales attributes."""

import torch.jit
import torch.nn as nn

from rllib.util.neural_networks.utilities import to_torch

from .abstract_transform import AbstractTransform


class Scaler(nn.Module):
    """Scaler Class."""

    def __init__(self, scale):
        super().__init__()
        self._scale = to_torch(scale)
        self._scale[self._scale == 0] = 1.0
        assert torch.all(self._scale > 0), "Scale must be positive."

    def forward(self, array):
        """See `AbstractTransform.__call__'."""
        array[..., :self._scale.shape[0]] = array[..., :self._scale.shape[0]] / self._scale
        return array

    @torch.jit.export
    def inverse(self, array):
        """See `AbstractTransform.inverse'."""
        array[..., :self._scale.shape[0]] = array[..., :self._scale.shape[0]] * self._scale
        return array


class RewardScaler(AbstractTransform):
    """Implementation of a Reward Scaler.

    Given a reward, it will scale it by dividing it by scale.

    Parameters
    ----------
    scale: float.
    """

    def __init__(self, scale):
        super().__init__()
        self._scaler = Scaler(scale)

    def forward(self, observation):
        """See `AbstractTransform.__call__'."""
        observation.reward = self._scaler(observation.reward)
        return observation

    @torch.jit.export
    def inverse(self, observation):
        """See `AbstractTransform.inverse'."""
        observation.reward = self._scaler.inverse(observation.reward)
        return observation


class ActionScaler(AbstractTransform):
    """Implementation of an Action Scaler.

    Given an action, it will scale it by dividing it by scale.

    Parameters
    ----------
    scale: float.

    """

    def __init__(self, scale):
        super().__init__()
        self._scaler = Scaler(scale)

    def forward(self, observation):
        """See `AbstractTransform.__call__'."""
        observation.action = self._scaler(observation.action)
        return observation

    @torch.jit.export
    def inverse(self, observation):
        """See `AbstractTransform.inverse'."""
        observation.action = self._scaler.inverse(observation.action)
        return observation
