"""Implementation of TRPO Algorithm."""

import torch.nn.modules.loss as loss
from torch.optim import Adam

from rllib.algorithms.trpo import TRPO
from rllib.policy import NNPolicy
from rllib.value_function import NNValueFunction

from .on_policy_agent import OnPolicyAgent


class TRPOAgent(OnPolicyAgent):
    """Implementation of the TRPO Agent.

    References
    ----------
    Schulman, J., Levine, S., Abbeel, P., Jordan, M., & Moritz, P. (2015).
    Trust region policy optimization. ICML.
    """

    def __init__(
        self,
        policy,
        value_function,
        optimizer,
        criterion,
        regularization=False,
        epsilon_mean=0.05,
        epsilon_var=None,
        lambda_=0.97,
        num_iter=80,
        target_update_frequency=1,
        train_frequency=0,
        num_rollouts=4,
        gamma=0.99,
        exploration_steps=0,
        exploration_episodes=0,
        tensorboard=False,
        comment="",
    ):
        self.algorithm = TRPO(
            value_function=value_function,
            policy=policy,
            regularization=regularization,
            epsilon_mean=epsilon_mean,
            epsilon_var=epsilon_var,
            criterion=criterion,
            lambda_=lambda_,
            gamma=gamma,
        )
        optimizer = type(optimizer)(
            [
                p
                for name, p in self.algorithm.named_parameters()
                if "target" not in name
            ],
            **optimizer.defaults,
        )

        super().__init__(
            optimizer=optimizer,
            num_iter=num_iter,
            target_update_frequency=target_update_frequency,
            train_frequency=train_frequency,
            num_rollouts=num_rollouts,
            gamma=gamma,
            exploration_steps=exploration_steps,
            exploration_episodes=exploration_episodes,
            tensorboard=tensorboard,
            comment=comment,
        )
        self.policy = self.algorithm.policy

    @classmethod
    def default(
        cls,
        environment,
        gamma=0.99,
        exploration_steps=0,
        exploration_episodes=0,
        tensorboard=False,
        test=False,
    ):
        """See `AbstractAgent.default'."""
        policy = NNPolicy(
            dim_state=environment.dim_state,
            dim_action=environment.dim_action,
            num_states=environment.num_states,
            num_actions=environment.num_actions,
            layers=[200, 200],
            biased_head=True,
            non_linearity="Tanh",
            squashed_output=True,
            action_scale=environment.action_scale,
            tau=5e-3,
            initial_scale=0.5,
            deterministic=False,
            goal=environment.goal,
            input_transform=None,
        )
        value_function = NNValueFunction(
            dim_state=environment.dim_state,
            num_states=environment.num_states,
            layers=[200, 200],
            biased_head=True,
            non_linearity="Tanh",
            tau=5e-3,
            input_transform=None,
        )

        optimizer = Adam(
            [
                {"params": policy.parameters(), "lr": 3e-4},
                {"params": value_function.parameters(), "lr": 1e-3},
            ]
        )
        criterion = loss.MSELoss

        return cls(
            policy=policy,
            value_function=value_function,
            optimizer=optimizer,
            criterion=criterion,
            regularization=False,
            epsilon_mean=0.05,
            epsilon_var=None,
            lambda_=0.95,
            num_iter=80,
            target_update_frequency=1,
            train_frequency=0,
            num_rollouts=4,
            gamma=gamma,
            exploration_steps=exploration_steps,
            exploration_episodes=exploration_episodes,
            tensorboard=tensorboard,
            comment=environment.name,
        )