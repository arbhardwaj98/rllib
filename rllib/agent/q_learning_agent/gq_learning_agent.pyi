from .q_learning_agent import QLearningAgent
from ..abstract_agent import State, Action, Reward, Done
from torch import Tensor
from typing import Tuple


class GQLearningAgent(QLearningAgent):

    def _td(self, state: State, action: Action, reward: Reward, next_state: State,
            done: Done) -> Tuple[Tensor, Tensor]: ...
