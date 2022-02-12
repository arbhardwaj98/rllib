"""ModelBasedAlgorithm."""
import torch

from rllib.dataset.experience_replay import ExperienceReplay

from .dyna import Dyna


class DataAugmentation(Dyna):
    """Data Augmentation Algorithm."""

    def __init__(
        self,
        memory=None,
        initial_state_dataset=None,
        initial_distribution=None,
        num_initial_state_samples=0,
        num_initial_distribution_samples=0,
        num_memory_samples=0,
        refresh_interval=2,
        model_batch_size=None,
        *args,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self.initial_distribution = initial_distribution
        self.initial_state_dataset = initial_state_dataset
        self.num_initial_state_samples = num_initial_state_samples
        self.num_initial_distribution_samples = num_initial_distribution_samples
        self.num_memory_samples = num_memory_samples
        self.memory = memory
        self.sim_memory = ExperienceReplay(
            max_len=memory.max_len,
            num_memory_steps=memory.num_memory_steps,
            transformations=memory.transformations,
        )
        self.model_batch_size = model_batch_size

        self.refresh_interval = refresh_interval
        self.count = 0

    def forward(self, observation):
        """Rollout model and call base algorithm with transitions."""
        real_loss = self.base_algorithm(observation)
        if self.only_real:
            return real_loss

        batch_size = self.model_batch_size or observation.reward.shape[0]
        if len(self.sim_memory) < batch_size:
            self.init_sim_memory(min_size=batch_size)
        sim_observation = self.sim_memory.sample_batch(batch_size)[0]
        sim_loss = self.base_algorithm(sim_observation)

        if self.only_sim:
            return sim_loss

        return real_loss + sim_loss

    def init_sim_memory(self, min_size=1000):
        """Initialize simulation memory with a minimum size."""
        while len(self.sim_memory) <= min_size:
            self.simulate(state=self._sample_initial_states(), policy=self.policy)

    def simulate(
        self, state, policy, initial_action=None, memory=None, stack_obs=False
    ):
        """Simulate from initial_states."""
        self.dynamical_model.eval()
        memory = self.sim_memory if memory is None else memory
        with torch.no_grad():
            trajectory = super().simulate(
                state, policy, stack_obs=stack_obs, memory=memory
            )

        return trajectory

    def _sample_initial_states(self):
        """Get initial states to sample from."""
        # Samples from experience replay empirical distribution.
        obs, *_ = self.memory.sample_batch(self.num_memory_samples)
        for transform in self.memory.transformations:
            obs = transform.inverse(obs)
        initial_states = obs.state[:, 0, :]  # obs is an n-step return.

        # Samples from empirical initial state distribution.
        if self.num_initial_state_samples > 0:
            initial_states_ = self.initial_state_dataset.sample_batch(
                self.num_initial_state_samples
            )
            initial_states = torch.cat((initial_states, initial_states_), dim=0)

        # Samples from initial distribution.
        if self.num_initial_distribution_samples > 0:
            initial_states_ = self.initial_distribution.sample(
                (self.num_initial_distribution_samples,)
            )
            initial_states = torch.cat((initial_states, initial_states_), dim=0)

        initial_states = initial_states.unsqueeze(0)
        return initial_states

    def update(self):
        """Update base algorithm."""
        if not self.only_real:
            self.simulate(state=self._sample_initial_states(), policy=self.policy)
        super().update()

    def reset(self):
        """Reset base algorithm."""
        self.count += 1
        if (self.count % self.refresh_interval) == 0:
            self.sim_memory.reset()
        super().reset()
