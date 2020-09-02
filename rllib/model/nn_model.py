"""Model implemented by a Neural Network."""
import torch

from rllib.util.neural_networks import CategoricalNN, HeteroGaussianNN, one_hot_encode

from .abstract_model import AbstractModel


class NNModel(AbstractModel):
    """Implementation of a Dynamical implemented with a Neural Network.

    Parameters
    ----------
    dim_state: Tuple
        dimension of state.
    dim_action: Tuple
        dimension of action.
    num_states: int, optional
        number of discrete states (None if state is continuous).
    num_actions: int, optional
        number of discrete actions (None if action is continuous).
    layers: list, optional
        width of layers, each layer is connected with a non-linearity.
    biased_head: bool, optional
        flag that indicates if head of NN has a bias term or not.

    """

    def __init__(
        self,
        layers=None,
        biased_head=True,
        non_linearity="Tanh",
        initial_scale=0.5,
        input_transform=None,
        deterministic=False,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.input_transform = input_transform

        out_dim = self._get_out_dim()
        in_dim = self._get_in_dim()
        assert len(out_dim) == 1, "No images allowed."

        if (
            self.discrete_state and self.model_kind == "dynamics"
        ) or self.model_kind == "termination":
            self.nn = CategoricalNN(
                in_dim=in_dim,
                out_dim=out_dim,
                layers=layers,
                biased_head=biased_head,
                non_linearity=non_linearity,
            )
        else:
            self.nn = HeteroGaussianNN(
                in_dim=in_dim,
                out_dim=out_dim,
                layers=layers,
                biased_head=biased_head,
                non_linearity=non_linearity,
                squashed_output=False,
                initial_scale=initial_scale,
            )

        self.deterministic = deterministic

    @classmethod
    def default(cls, environment, *args, **kwargs):
        """See AbstractModel.default()."""
        if environment.num_states > 0:
            width = 20 * environment.num_states
        else:
            width = 20 * environment.dim_state[0]
        depth = 2
        return super().default(
            environment,
            layers=kwargs.pop("layers", [width] * depth),
            biased_head=kwargs.pop("biased_head", True),
            non_linearity=kwargs.pop("non_linearity", "Swish"),
            initial_scale=kwargs.pop("initial_scale", 0.5),
            input_transform=kwargs.pop("input_transform", None),
            deterministic=kwargs.pop("deterministic", False),
            *args,
            **kwargs,
        )

    def forward(self, state, action, next_state=None):
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

    @property
    def name(self):
        """Get Model name."""
        return f"{'Deterministic' if self.deterministic else 'Probabilistic'} Ensemble"

    def _get_out_dim(self):
        if self.model_kind == "dynamics":
            if self.discrete_state:
                out_dim = (self.num_states,)
            else:
                out_dim = self.dim_state
        else:
            out_dim = (1,)
        return out_dim

    def _get_in_dim(self):
        if self.discrete_state:
            in_dim = self.num_states
        else:
            in_dim = self.dim_state[0]

        if self.discrete_action:
            in_dim += self.num_actions
        else:
            in_dim += self.dim_action[0]

        if hasattr(self.input_transform, "extra_dim"):
            in_dim = in_dim + getattr(self.input_transform, "extra_dim")

        return (in_dim,)
