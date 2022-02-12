from typing import Any

from torch import Tensor

from rllib.dataset.datatypes import TupleDistribution

from .abstract_policy import AbstractPolicy

class ZeroPolicy(AbstractPolicy):
    def __init__(self, *args: Any, **kwargs: Any) -> None: ...
    def forward(self, *args: Tensor, **kwargs: Any) -> TupleDistribution: ...
