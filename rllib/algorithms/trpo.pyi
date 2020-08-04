from typing import Any, List, Optional, Tuple, Type, Union

import torch.nn as nn
from torch import Tensor
from torch.nn.modules.loss import _Loss

from rllib.algorithms.gae import GAE
from rllib.dataset.datatypes import Observation
from rllib.policy import AbstractPolicy
from rllib.util.parameter_decay import ParameterDecay
from rllib.value_function import AbstractValueFunction

from .abstract_algorithm import AbstractAlgorithm, TRPOLoss

class TRPO(AbstractAlgorithm):

    old_policy: AbstractPolicy
    value_function: AbstractValueFunction
    value_function_target: AbstractValueFunction

    epsilon_mean: Tensor
    epsilon_var: Tensor
    eta_mean: ParameterDecay
    eta_var: ParameterDecay

    value_loss_criterion: _Loss
    gae: GAE
    eps: float
    def __init__(
        self,
        value_function: AbstractValueFunction,
        criterion: Type[_Loss] = ...,
        regularization: bool = ...,
        epsilon_mean: Union[ParameterDecay, float] = ...,
        epsilon_var: Optional[Union[ParameterDecay, float]] = ...,
        lambda_: float = ...,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
    def get_log_p_and_kl(
        self, state: Tensor, action: Tensor
    ) -> Tuple[Tensor, Tensor, Tensor, Tensor,]: ...
    def get_advantage_and_value_target(
        self, trajectory: Observation
    ) -> Tuple[Tensor, Tensor]: ...
    def forward_slow(self, trajectories: List[Observation]) -> TRPOLoss: ...
    def forward(self, trajectories: List[Observation], **kwargs: Any) -> TRPOLoss: ...
