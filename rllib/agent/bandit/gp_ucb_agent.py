"""Implementation of GP-UCB algorithm."""

import gpytorch
import torch

from rllib.agent import AbstractAgent
from rllib.policy import AbstractPolicy
from rllib.util.parameter_decay import ParameterDecay, Constant
from rllib.util.gaussian_processes import SparseGP
from rllib.util.gaussian_processes.utilities import add_data_to_gp, bkb


class GPUCBPolicy(AbstractPolicy):
    """GP UCB Policy.

    Implementation of GP-UCB algorithm.
    GP-UCB uses a GP to maintain the predictions of a distribution over actions.

    The algorithm selects the action as:
    x = arg max mean(x) + beta * std(x)
    where mean(x) and std(x) are the mean and standard devations of the GP at loc x.

    Parameters
    ----------
    gp: initialized GP model.
    x: discretization of domain.
    beta: exploration parameter.

    References
    ----------
    Srinivas, N., Krause, A., Kakade, S. M., & Seeger, M. (2009).
    Gaussian process optimization in the bandit setting: No regret and experimental
    design.
    """

    def __init__(self, gp, x, beta=2.0):
        super().__init__(dim_state=1, dim_action=x.shape[0],
                         num_states=1, num_actions=-1, deterministic=True)
        self.gp = gp
        self.gp.eval()
        self.gp.likelihood.eval()
        self.x = x
        if not isinstance(beta, ParameterDecay):
            beta = Constant(beta)
        self.beta = beta

    def forward(self, state):
        """Call the GP-UCB algorithm."""
        with torch.no_grad(), gpytorch.settings.fast_pred_var():
            pred = self.gp(self.x)
            ucb = pred.mean + self.beta() * pred.stddev

            max_id = torch.argmax(ucb)
            next_point = self.x[[[max_id]]]
            return next_point, torch.zeros(1)

    def update(self):
        """Update policy parameters."""
        self.beta.update()


class GPUCBAgent(AbstractAgent):
    """Agent that implements the GP-UCB algorithm.

    Parameters
    ----------
    gp: initialized GP model.
    x: discretization of domain.
    beta: exploration parameter.

    References
    ----------
    Srinivas, N., Krause, A., Kakade, S. M., & Seeger, M. (2009).
    Gaussian process optimization in the bandit setting: No regret and experimental
    design. ICML.

    Calandriello, D., Carratino, L., Lazaric, A., Valko, M., & Rosasco, L. (2019).
    Gaussian process optimization with adaptive sketching: Scalable and no regret. COLT.

    Chowdhury, S. R., & Gopalan, A. (2017).
    On kernelized multi-armed bandits. JMLR.
    """

    def __init__(self, env_name, gp, x, beta=2.0):
        self.policy = GPUCBPolicy(gp, x, beta)
        super().__init__(env_name, train_frequency=1, num_rollouts=0, gamma=1,
                         exploration_episodes=0, exploration_steps=0, comment=gp.name)

    def observe(self, observation) -> None:
        """Observe and update GP."""
        super().observe(observation)  # Already calls self.policy.update()
        add_data_to_gp(self.policy.gp, observation.action.unsqueeze(-1),
                       observation.reward)
        self.logger.update(num_gp_inputs=len(self.policy.gp.train_targets))
        if isinstance(self.policy.gp, SparseGP):
            inducing_points = torch.cat(
                (self.policy.gp.xu, observation.action.unsqueeze(-1)), dim=-2)

            inducing_points = bkb(self.policy.gp, inducing_points)
            self.policy.gp.set_inducing_points(inducing_points)
            self.logger.update(num_inducing_points=self.policy.gp.xu.shape[0])