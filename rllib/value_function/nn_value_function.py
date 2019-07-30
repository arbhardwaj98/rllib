from .abstract_value_function import AbstractValueFunction, AbstractQFunction
from rllib.util.neural_networks import DeterministicNN
import torch
from rllib.util import update_parameters


class NNValueFunction(AbstractValueFunction):
    def __init__(self, dim_state, num_states=None,
                 layers=None, tau=1.0):
        super().__init__(dim_state, num_states)

        if self.discrete_state:
            num_inputs = self.num_states
        else:
            num_inputs = self.dim_state

        self._value_function = DeterministicNN(num_inputs, 1, layers)
        self._tau = tau

    def __str__(self):
        return "Neural Network Value function approximation"

    def __call__(self, state, action=None):
        return self._value_function(state)

    @property
    def parameters(self):
        return self._value_function.parameters()

    @parameters.setter
    def parameters(self, new_params):
        update_parameters(self._value_function.parameters(), new_params, self._tau)


class NNQFunction(AbstractQFunction):
    def __init__(self, dim_state, dim_action, num_states=None, num_actions=None,
                 layers=None, tau=1.0):
        super().__init__(dim_state, dim_action, num_states, num_actions)

        if not self.discrete_state and not self.discrete_action:
            num_inputs = self.dim_state + self.dim_action
            num_outputs = 1
        elif self.discrete_state and self.discrete_action:
            num_inputs = self.num_states
            num_outputs = self.num_actions
        elif not self.discrete_state and self.discrete_action:
            num_inputs = self.dim_state
            num_outputs = self.num_actions
        else:
            raise ValueError("If states are discrete, so should be actions.")

        self._q_function = DeterministicNN(num_inputs, num_outputs, layers)
        self._tau = tau

    def __str__(self):
        return "Neural Network Q function approximation"

    def __call__(self, state, action=None):
        if action is None:
            if not self.discrete_action:
                raise NotImplementedError
            elif not self.discrete_state:
                return self._q_function(state)
            else:
                in_ = torch.scatter(torch.zeros(self.num_states), 0, state, 1)
                return self._q_function(in_).gather(1, action.unsqueeze(-1)).squeeze(-1)

        if not self.discrete_state and not self.discrete_action:
            state_action = torch.cat((state, action), dim=-1)
            return self._q_function(state_action)
        elif self.discrete_state and self.discrete_action:
            in_ = torch.scatter(torch.zeros(self.num_states), 0, state, 1)
            return self._q_function(in_).gather(1, action.unsqueeze(-1)).squeeze(-1)
        elif not self.discrete_state and self.discrete_action:
            return self._q_function(state).gather(1, action.unsqueeze(-1)).squeeze(-1)
        else:
            raise ValueError("If states are discrete, so should be actions.")

    @property
    def parameters(self):
        return self._q_function.parameters()

    @parameters.setter
    def parameters(self, new_params):
        update_parameters(self._q_function.parameters(), new_params, self._tau)

    def max(self, state):
        if not self.discrete_action:
            raise NotImplementedError
        else:
            return self._q_function(state).max(dim=-1)[0]

    def argmax(self, state):
        if not self.discrete_action:
            raise NotImplementedError
        else:
            return self._q_function(state).argmax(dim=-1)