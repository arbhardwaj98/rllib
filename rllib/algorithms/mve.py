"""Model Based Value Expansion Algorithm."""
import torch

from rllib.dataset.datatypes import Loss
from rllib.dataset.utilities import stack_list_of_tuples
from rllib.util.neural_networks.utilities import broadcast_to_tensor
from rllib.util.value_estimation import discount_cumsum, mc_return
from rllib.value_function import NNEnsembleQFunction

from .dyna import Dyna


class MVE(Dyna):
    """Derived Algorithm using MVE to calculate targets.

    References
    ----------
    Feinberg, V., et. al. (2018).
    Model-based value estimation for efficient model-free reinforcement learning.
    arXiv.
    """

    def __init__(self, td_k=False, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.td_k = td_k

    def forward(self, observation):
        """Rollout model and call base algorithm with transitions."""
        self.base_algorithm.reset_info()
        loss = Loss()
        loss += self.base_algorithm.actor_loss(observation).reduce("mean")
        loss += self.model_augmented_critic_loss(observation).reduce("mean")
        loss += self.base_algorithm.regularization_loss(observation).reduce("mean")
        return loss

    def model_augmented_critic_loss(self, observation):
        """Get Model-Based critic-loss."""
        with torch.no_grad():
            state, action = observation.state[..., 0, :], observation.action[..., 0, :]
            sim_trajectory = self.simulation_algorithm.simulate(
                state, self.policy, initial_action=action
            )
            sim_observation = stack_list_of_tuples(sim_trajectory, dim=-2)

        if not self.td_k:
            sim_observation.state = observation.state[..., :1, :]
            sim_observation.action = observation.action[..., :1, :]

        pred_q = self.base_algorithm.get_value_prediction(sim_observation)

        # Get target_q with semi-gradients.
        with torch.no_grad():
            target_q = self.get_value_target(sim_observation)
            if not self.td_k:
                target_q = target_q.reshape(
                    self.num_particles,
                    *pred_q.shape[:-2],
                    self.simulation_algorithm.reward_model.dim_reward[0],
                ).mean(0)
                # take the mean of the particles.
            if pred_q.shape != target_q.shape:  # Reshape in case of ensembles.
                assert isinstance(self.critic, NNEnsembleQFunction)
                target_q = target_q.unsqueeze(-1).repeat_interleave(
                    self.critic.num_heads, -1
                )

        critic_loss = self.base_algorithm.criterion(pred_q, target_q)

        return Loss(critic_loss=critic_loss)

    def get_value_target(self, observation):
        """Rollout model and call base algorithm with transitions."""
        if self.td_k:
            reward = observation.reward
            final_state = observation.next_state[..., -1, :]
            not_done = 1 - observation.done[..., -1]
            final_value = self.base_algorithm.value_function(final_state)

            if final_value.ndim == observation.reward.ndim:  # It is an ensemble.
                final_min = final_value.min(-1)[0]
                final_max = final_value.max(-1)[0]
                weight = self.critic_ensemble_lambda
                final_value = weight * final_min + (1.0 - weight) * final_max
            tau = self.base_algorithm.entropy_loss.eta.item()
            entropy = broadcast_to_tensor(observation.entropy, target_tensor=reward)
            not_done = broadcast_to_tensor(not_done, target_tensor=final_value)
            rewards = torch.cat(
                (reward + tau * entropy, (final_value * not_done).unsqueeze(-2)), dim=-2
            )
            sim_target = discount_cumsum(
                rewards,
                gamma=self.base_algorithm.gamma,
                reward_transformer=self.base_algorithm.reward_transformer,
            )[..., :-1, :]
            # remove last time step
        else:
            sim_target = mc_return(
                observation,
                gamma=self.base_algorithm.gamma,
                td_lambda=self.td_lambda,
                value_function=self.base_algorithm.value_function,
                reward_transformer=self.base_algorithm.reward_transformer,
                entropy_regularization=self.base_algorithm.entropy_loss.eta.item(),
                reduction="min",
            )

        return sim_target
