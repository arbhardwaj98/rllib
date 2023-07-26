"""Model implemented by a Neural Network."""
import torch

from rllib.util.neural_networks.neural_networks import CategoricalNN, HeteroGaussianNN, HomoGaussianNN
from rllib.util.neural_networks.utilities import one_hot_encode

from .abstract_model import AbstractModel


class NNModel(AbstractModel):
    """Implementation of a Dynamical implemented with a Neural Network.

    Parameters
    ----------
    layers: list, optional (default=No layers).
        width of layers, each layer is connected with a non-linearity.
    biased_head: bool, optional (default=True).
        flag that indicates if head of NN has a bias term or not.
    non_linearity: string, optional (default=Tanh).
        Neural Network non-linearity.
    input_transform: nn.Module, optional (default=None).
        Module with which to transform inputs.
    per_coordinate: bool, optional (default = True).
        Flag that indicates if there is an independent model per coordinate.
    heteroscedastic: bool, optional (default = True).
        Flag that indicates whether to use a head for variance prediction or use a fixed variance.
    in_dim: int, optional (default=None).
        Input dimension of the model if different from the environment's state-action space.
    out_dim: int, optional (default=None).
        Output dimension of the model if different from the environment's state space.
    """

    def __init__(
        self,
        layers=(200, 200, 200),
        biased_head=True,
        non_linearity="Swish",
        initial_scale=0.5,
        input_transform=None,
        per_coordinate=False,
        heteroscedastic=True,
        jit_compile=False,
        in_dim=None,
        out_dim=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.input_transform = input_transform

        out_dim = self._get_out_dim() if out_dim is None else out_dim
        in_dim = self._get_in_dim() if in_dim is None else in_dim
        assert len(out_dim) == 1, "No images allowed."

        if (
            self.discrete_state and self.model_kind == "dynamics"
        ) or self.model_kind == "termination":
            if jit_compile:
                self.nn = torch.nn.ModuleList(
                    [
                        torch.jit.script(
                            CategoricalNN(
                                in_dim=in_dim,
                                out_dim=out_dim,
                                layers=layers,
                                biased_head=biased_head,
                                non_linearity=non_linearity,
                            )
                        )
                    ]
                )
            else:
                self.nn = torch.nn.ModuleList(
                    [
                        CategoricalNN(
                            in_dim=in_dim,
                            out_dim=out_dim,
                            layers=layers,
                            biased_head=biased_head,
                            non_linearity=non_linearity,
                        )
                    ]
                )
        elif per_coordinate:
            if heteroscedastic:
                if jit_compile:
                    self.nn = torch.nn.ModuleList(
                        [
                            torch.jit.script(
                                HeteroGaussianNN(
                                    in_dim=in_dim,
                                    out_dim=(1,),
                                    layers=layers,
                                    biased_head=biased_head,
                                    non_linearity=non_linearity,
                                    squashed_output=False,
                                    initial_scale=initial_scale,
                                )
                                for _ in range(out_dim[0])
                            )
                        ]
                    )
                else:
                    self.nn = torch.nn.ModuleList(
                        [
                            HeteroGaussianNN(
                                in_dim=in_dim,
                                out_dim=(1,),
                                layers=layers,
                                biased_head=biased_head,
                                non_linearity=non_linearity,
                                squashed_output=False,
                                initial_scale=initial_scale,
                            )
                            for _ in range(out_dim[0])
                        ]
                    )
            else:
                if jit_compile:
                    self.nn = torch.nn.ModuleList(
                        [
                            torch.jit.script(
                                HomoGaussianNN(
                                    in_dim=in_dim,
                                    out_dim=(1,),
                                    layers=layers,
                                    biased_head=biased_head,
                                    non_linearity=non_linearity,
                                    squashed_output=False,
                                    initial_scale=initial_scale,
                                )
                                for _ in range(out_dim[0])
                            )
                        ]
                    )
                else:
                    self.nn = torch.nn.ModuleList(
                        [
                            HomoGaussianNN(
                                in_dim=in_dim,
                                out_dim=(1,),
                                layers=layers,
                                biased_head=biased_head,
                                non_linearity=non_linearity,
                                squashed_output=False,
                                initial_scale=initial_scale,
                            )
                            for _ in range(out_dim[0])
                        ]
                    )

        else:
            if heteroscedastic:
                if jit_compile:
                    self.nn = torch.nn.ModuleList(
                        [
                            torch.jit.script(
                                HeteroGaussianNN(
                                    in_dim=in_dim,
                                    out_dim=out_dim,
                                    layers=layers,
                                    biased_head=biased_head,
                                    non_linearity=non_linearity,
                                    squashed_output=False,
                                    initial_scale=initial_scale,
                                )
                            )
                        ]
                    )
                else:
                    self.nn = torch.nn.ModuleList(
                        [
                            HeteroGaussianNN(
                                in_dim=in_dim,
                                out_dim=out_dim,
                                layers=layers,
                                biased_head=biased_head,
                                non_linearity=non_linearity,
                                squashed_output=False,
                                initial_scale=initial_scale,
                            )
                        ]
                    )
            else:
                if jit_compile:
                    self.nn = torch.nn.ModuleList(
                        [
                            torch.jit.script(
                                HomoGaussianNN(
                                    in_dim=in_dim,
                                    out_dim=out_dim,
                                    layers=layers,
                                    biased_head=biased_head,
                                    non_linearity=non_linearity,
                                    squashed_output=False,
                                    initial_scale=initial_scale,
                                )
                            )
                        ]
                    )
                else:
                    self.nn = torch.nn.ModuleList(
                        [
                            HomoGaussianNN(
                                in_dim=in_dim,
                                out_dim=out_dim,
                                layers=layers,
                                biased_head=biased_head,
                                non_linearity=non_linearity,
                                squashed_output=False,
                                initial_scale=initial_scale,
                            )
                        ]
                    )

    @classmethod
    def default(cls, environment, *args, **kwargs):
        """See AbstractModel.default()."""
        return super().default(environment, *args, **kwargs)

    def state_actions_to_input_data(self, state, action):
        """Process state-action pairs."""
        if self.discrete_state:
            state = one_hot_encode(state, num_classes=self.num_states)
        if self.discrete_action:
            action = one_hot_encode(action, num_classes=self.num_actions)

        if self.input_transform is not None:
            state = self.input_transform(state)

        state_action = torch.cat((state, action), dim=-1)
        return state_action

    def stack_predictions(self, mean_std_dim):
        """Stack Predictions and scale by temperature."""
        if self.discrete_state:
            logits = torch.stack(
                tuple(mean_std[0][..., 0] for mean_std in mean_std_dim), -1
            )
            return self.temperature * logits
        if len(mean_std_dim) == 1:  # Only 1 NN.
            mean, scale_tril = mean_std_dim[0]
        else:  # There is a NN per dimension.
            mean = torch.stack(
                tuple(mean_std[0][..., 0] for mean_std in mean_std_dim), -1
            )
            stddev = torch.stack(
                tuple(mean_std[1][..., 0, 0] for mean_std in mean_std_dim), -1
            )
            scale_tril = torch.diag_embed(stddev)

        if self.deterministic:
            return mean, torch.zeros_like(scale_tril)
        return mean, self.temperature * scale_tril

    def forward(self, state, action, next_state=None):
        """Get Next-State distribution."""
        state_action = self.state_actions_to_input_data(state, action)
        mean_std_dim = [nn(state_action) for nn in self.nn]
        return self.stack_predictions(mean_std_dim)

    @property
    def name(self):
        """Get Model name."""
        return f"{'Deterministic' if self.deterministic else 'Probabilistic'} NN"

    def _get_out_dim(self):
        if self.model_kind == "dynamics":
            if self.discrete_state:
                out_dim = (self.num_states,)
            else:
                out_dim = self.dim_state
        elif self.model_kind == "rewards":
            out_dim = self.dim_reward
        elif self.model_kind == "termination":
            out_dim = 1
        else:
            raise NotImplementedError(f"{self.model_kind} not implemented.")
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

        if self.input_transform is not None:
            in_dim = in_dim + self.input_transform.extra_dim

        return (in_dim,)
