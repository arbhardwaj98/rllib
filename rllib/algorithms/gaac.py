"""Generalized Advantage Actor-Critic Algorithm."""
from rllib.algorithms.policy_evaluation.gae import GAE
from rllib.util.neural_networks.utilities import broadcast_to_tensor

from .ac import ActorCritic


class GAAC(ActorCritic):
    r"""Implementation of Generalized Advantage Actor-Critic algorithm.

    GAAC is an on-policy model-free control algorithm.
    GAAC estimates the returns using GAE-lambda.

    GAAC estimates the gradient as:
    .. math:: \grad J = \int_{\tau} \grad \log \pi(s_t) GAE_\lambda(\tau),
    where the previous integral is computed through samples (s_t, a_t) samples.

    Parameters
    ----------
    policy: AbstractPolicy
        Policy to optimize.
    critic: AbstractQFunction
        Critic that evaluates the current policy.
    criterion: _Loss
        Criterion to optimize the baseline.
    gamma: float
        Discount factor.

    References
    ----------
    Schulman, J., Moritz, P., Levine, S., Jordan, M., & Abbeel, P. (2015).
    High-dimensional continuous control using generalized advantage estimation. ICLR.
    """

    def __init__(self, td_lambda=0.95, *args, **kwargs):
        super().__init__(td_lambda=td_lambda, *args, **kwargs)
        self.gae = GAE(
            td_lambda=td_lambda, gamma=self.gamma, value_function=self.critic_target
        )

    def returns(self, trajectory):
        """Estimate the returns of a trajectory."""
        state, action = trajectory.state, trajectory.action
        weight = self.get_ope_weight(state, action, trajectory.log_prob_action)
        advantage = self.gae(trajectory)
        weight = broadcast_to_tensor(input_tensor=weight, target_tensor=advantage)
        return weight * advantage  # GAE returns.
