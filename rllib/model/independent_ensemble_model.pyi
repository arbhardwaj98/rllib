"""Implementation of a model composed by an ensemble of independent models."""

from typing import Any

import numpy as np
import torch

from .abstract_model import AbstractModel

class IndependentEnsembleModel(AbstractModel):
    num_heads: int
    prediction_strategy: str
    models: torch.nn.ModuleList
    head_ptr: int
    def __init__(
        self,
        models: torch.nn.ModuleList,
        prediction_strategy: str = ...,
        *args: Any,
        **kwargs: Any,
    ) -> None: ...
