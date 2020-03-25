"""Model implemented by a Neural Network."""
import torch

from rllib.util.neural_networks import CategoricalNN, HeteroGaussianNN, one_hot_encode
from .abstract_model import AbstractModel


class NNModel(AbstractModel):
    """Implementation of a Dynamical implemented with a Neural Network.

    Parameters
    ----------
    dim_state: int
        dimension of state.
    dim_action: int
        dimension of action.
    num_states: int, optional
        number of discrete states (None if state is continuous).
    num_actions: int, optional
        number of discrete actions (None if action is continuous).
    layers: list, optional
        width of layers, each layer is connected with ReLUs non-linearities.
    biased_head: bool, optional
        flag that indicates if head of NN has a bias term or not.

    """

    def __init__(self, dim_state, dim_action, num_states=-1, num_actions=-1,
                 layers=None, biased_head=True, non_linearity='ReLU',
                 input_transform=None, deterministic=False):
        super().__init__(dim_state, dim_action, num_states=num_states,
                         num_actions=num_actions)
        self.input_transform = input_transform

        if self.discrete_state:
            out_dim = self.num_states
        else:
            out_dim = self.dim_state

        if self.discrete_action:
            in_dim = out_dim + self.num_actions
        else:
            in_dim = out_dim + self.dim_action

        if hasattr(input_transform, 'extra_dim'):
            in_dim += getattr(input_transform, 'extra_dim')

        if self.discrete_action:
            self.nn = CategoricalNN(in_dim, out_dim, layers, biased_head=biased_head,
                                    non_linearity=non_linearity)
        else:
            self.nn = HeteroGaussianNN(in_dim, out_dim, layers, biased_head=biased_head,
                                       non_linearity=non_linearity,
                                       squashed_output=False)

        self.deterministic = deterministic

    def forward(self, state, action):
        """Get Next-State distribution."""
        if self.discrete_state:
            state = one_hot_encode(state.long(), num_classes=self.num_states)
        if self.discrete_action:
            action = one_hot_encode(action.long(), num_classes=self.num_actions)

        if self.input_transform is not None:
            state = self.input_transform(state)

        state_action = torch.cat((state, action), dim=-1)
        next_state = self.nn(state_action)

        if self.deterministic:
            return next_state[0], torch.zeros_like(next_state[1])
        return next_state