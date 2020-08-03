from typing import Any

import torch.nn as nn
from torch import Tensor
from torch.nn.modules.loss import _Loss

from rllib.value_function import AbstractQFunction

from .abstract_algorithm import AbstractAlgorithm, TDLoss

class SARSA(AbstractAlgorithm):
    q_function: AbstractQFunction
    q_target: AbstractQFunction
    criterion: _Loss
    gamma: float
    def __init__(
        self, q_function: AbstractQFunction, criterion: _Loss, gamma: float
    ) -> None: ...
    def get_q_target(
        self, reward: Tensor, next_state: Tensor, done: Tensor, next_action: Tensor
    ) -> Tensor: ...
    def forward(self, *args: Tensor, **kwargs: Any) -> TDLoss: ...
    def _build_return(self, pred_q: Tensor, target_q: Tensor) -> TDLoss: ...
    def update(self) -> None: ...

class GradientSARSA(SARSA): ...
