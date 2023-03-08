"""Helper functions to conduct a rollout with policies or agents."""

import time
import torch
from gym.wrappers.monitoring.video_recorder import VideoRecorder
from tqdm import tqdm

from rllib.dataset.datatypes import Observation
from rllib.util.neural_networks.utilities import broadcast_to_tensor, to_torch
from rllib.util.training.utilities import Evaluate
from rllib.util.utilities import (
    get_entropy_and_log_p,
    sample_model,
    tensor_to_distribution,
)


def step_env(environment, state, action, action_scale, pi=None, render=False):
    """Perform a single step in an environment."""
    try:
        next_state, reward, done, info = environment.step(action)
    except TypeError:
        next_state, reward, done, info = environment.step(action.item())

    action = to_torch(action)

    if pi is not None:
        try:
            with torch.no_grad():
                entropy, log_prob_action = get_entropy_and_log_p(
                    pi, action, action_scale
                )
        except RuntimeError:
            entropy, log_prob_action = 0.0, 1.0
    else:
        entropy, log_prob_action = 0.0, 1.0

    observation = Observation(
        state=state,
        action=action,
        reward=reward,
        next_state=next_state,
        done=done,
        entropy=entropy,
        log_prob_action=log_prob_action,
    ).to_torch()
    state = next_state
    if render:
        environment.render()
    return observation, state, done, info


def step_model(
    dynamical_model,
    reward_model,
    termination_model,
    state,
    action,
    done=None,
    action_scale=1.0,
    pi=None,
):
    """Perform a single step in an dynamical model."""
    # Sample a next state
    next_state = sample_model(dynamical_model, state, action)

    # Sample a reward
    reward = sample_model(reward_model, state, action, next_state)

    if done is None:
        done = torch.zeros_like(reward).bool()
    broadcast_done = broadcast_to_tensor(done, target_tensor=reward)
    reward *= (~broadcast_done).float()

    # Check for termination.
    if termination_model is not None:
        done_ = sample_model(termination_model, state, action, next_state).bool()
        done = done + done_  # "+" is a boolean "or".

    if pi is not None:
        try:
            entropy, log_prob_action = get_entropy_and_log_p(pi, action, action_scale)
        except RuntimeError:
            entropy, log_prob_action = 0.0, 1.0
    else:
        entropy, log_prob_action = 0.0, 1.0

    observation = Observation(
        state=state,
        action=action,
        reward=reward,
        next_state=next_state,
        done=done.float(),
        entropy=entropy,
        log_prob_action=log_prob_action,
    ).to_torch()

    return observation, next_state, done


def record(environment, agent, path, num_episodes=1, max_steps=1000):
    """Record an episode."""
    recorder = VideoRecorder(environment, path=path)
    for _ in range(num_episodes):
        state = environment.reset()
        agent.set_goal(environment.goal)

        done = False
        time_step = 0
        while not done:
            action = agent.act(state)
            observation, state, done, info = step_env(
                environment, state, action, agent.policy.action_scale
            )
            recorder.capture_frame()

            time_step += 1
            if max_steps <= time_step:
                break

    recorder.close()


def rollout_episode(
    environment, agent, max_steps, render, callback_frequency, callbacks, use_early_termination=True,
):
    """Rollout a full episode."""
    state = environment.reset()
    agent.set_goal(environment.goal)
    agent.start_episode()
    done = False
    start_time = time.time()
    time_step = 0
    while not done:
        action = agent.act(state)  # Scaled action, not in (-1, 1)
        obs, state, done, info = step_env(
            environment=environment,
            state=state,
            action=action,
            action_scale=agent.policy.action_scale,
            pi=agent.pi,
            render=render,
        )
        agent.observe(obs)
        # Log info.
        agent.logger.update(**info)

        if not use_early_termination:
            done = (max_steps <= time_step)

        time_step += 1
        if max_steps <= time_step:
            break

    # TODO: Check this callback
    if callback_frequency and agent.total_episodes % callback_frequency == 0:
        for callback in callbacks:
            pass
            # callback(agent, environment, agent.total_episodes)
    agent.end_episode()
    print(f"Episode_time: {time.time() - start_time}")


def rollout_agent(
    environment,
    agent,
    num_episodes=1,
    max_steps=1000,
    render=False,
    use_early_termination=True,
    print_frequency=1,
    callback_frequency=0,
    eval_frequency=0,
    save_milestones=None,
    callbacks=None,
):
    """Conduct a rollout of an agent in an environment.

    Parameters
    ----------
    environment: AbstractEnvironment
        Environment with which the abstract interacts.
    agent: AbstractAgent
        Agent that interacts with the environment.
    num_episodes: int, optional (default=1)
        Number of episodes.
    max_steps: int.
        Maximum number of steps per episode.
    render: bool.
        Flag that indicates whether to render the environment or not.
    print_frequency: int, optional.
        Print agent stats every `print_frequency' episodes if > 0.
    callback_frequency: int, optional.
        Plot agent callbacks every `plot_frequency' episodes if > 0.
    eval_frequency: int, optional.
        Evaluate agent every 'eval_frequency' episodes if > 0.
    save_milestones: List[int], optional.
        List with episodes in which to save the agent.
    callbacks: List[Callable[[AbstractAgent, AbstractEnvironment,int], None]], optional.
        List of functions for evaluating/plotting the agent.
    """
    save_milestones = list() if save_milestones is None else save_milestones
    callbacks = list() if callbacks is None else callbacks
    for episode in tqdm(range(num_episodes)):
        rollout_episode(
            environment=environment,
            agent=agent,
            max_steps=max_steps,
            render=render,
            callback_frequency=callback_frequency,
            use_early_termination=use_early_termination,
            callbacks=callbacks,
        )

        if print_frequency and episode % print_frequency == 0:
            print(agent)

        if episode in save_milestones:
            agent.save(f"{agent.name}_{episode}.pkl")

        if eval_frequency and episode % eval_frequency == 0:
            with Evaluate(agent):
                rollout_episode(
                    environment=environment,
                    agent=agent,
                    max_steps=max_steps,
                    render=render,
                    callback_frequency=callback_frequency,
                    use_early_termination=use_early_termination,
                    callbacks=callbacks,
                )
    agent.end_interaction()


def rollout_policy(
    environment, policy, num_episodes=1, max_steps=1000, render=False, memory=None
):
    """Conduct a rollout of a policy in an environment.

    Parameters
    ----------
    environment: AbstractEnvironment
        Environment with which the policy interacts.
    policy: AbstractPolicy
        Policy that interacts with the environment.
    num_episodes: int, optional (default=1)
        Number of episodes.
    max_steps: int.
        Maximum number of steps per episode.
    render: bool.
        Flag that indicates whether to render the environment or not.
    memory: ExperienceReplay, optional.
        Memory where to store the simulated transitions.

    Returns
    -------
    trajectories: List[Trajectory]=List[List[Observation]]
        A list of trajectories.

    """
    trajectories = []
    for _ in tqdm(range(num_episodes)):
        state = environment.reset()
        done = False
        trajectory = []
        time_step = 0
        while not done:
            pi = tensor_to_distribution(policy(to_torch(state)), **policy.dist_params)
            action = pi.sample()
            if not policy.discrete_action:
                action = policy.action_scale * action.clamp(-1.0, 1.0)
            obs, state, done, info = step_env(
                environment=environment,
                state=state,
                action=action.detach().numpy(),
                action_scale=policy.action_scale,
                pi=pi,
                render=render,
            )
            trajectory.append(obs)
            if memory is not None:
                memory.append(obs)

            time_step += 1
            if max_steps <= time_step:
                break

        trajectories.append(trajectory)
    return trajectories


def rollout_model(
    dynamical_model,
    reward_model,
    policy,
    initial_state,
    initial_action=None,
    termination_model=None,
    max_steps=1000,
    memory=None,
    detach_state=False,
):
    """Conduct a rollout of a policy interacting with a model.

    Parameters
    ----------
    dynamical_model: AbstractModel
        Dynamical Model with which the policy interacts.
    reward_model: AbstractModel.
        Reward Model with which the policy interacts.
    policy: AbstractPolicy
        Policy that interacts with the environment.
    initial_state: State
        Starting states for the interaction.
    initial_action: Action.
        Starting action for the interaction.
    termination_model: AbstractModel.
        Termination condition to finish the rollout.
    max_steps: int.
        Maximum number of steps per episode.
    memory: ExperienceReplay, optional.
        Memory where to store the simulated transitions.
    detach_state: Bool, optional
        Detach state from computation graph for policy. Useful for BPTT.

    Returns
    -------
    trajectory: Trajectory=List[Observation]
        A list of observations.

    Notes
    -----
    It will try to do the re-parametrization trick with the policy and models.

    TODO: Parallelize it!.
    """
    trajectory = list()
    state = initial_state
    done = torch.full(state.shape[:-1], False, dtype=torch.bool)

    assert max_steps > 0
    for i in range(max_steps):
        if policy is not None:
            if detach_state:
                pi = tensor_to_distribution(policy(state.clone().detach()), **policy.dist_params)
            else:
                pi = tensor_to_distribution(policy(state), **policy.dist_params)
            action_scale = policy.action_scale
        else:
            assert max_steps == 1
            pi, action_scale = None, 1.0

        if i == 0 and initial_action is not None:
            action = initial_action
        else:
            # Sample an action
            if pi.has_rsample:
                action = pi.rsample()
            else:
                action = pi.sample()
            if not policy.discrete_action:
                action = policy.action_scale * action.clamp_(-1.0, 1.0)

        observation, next_state, done = step_model(
            dynamical_model=dynamical_model,
            reward_model=reward_model,
            termination_model=termination_model,
            state=state,
            action=action,
            action_scale=action_scale,
            done=done,
            pi=pi,
        )
        trajectory.append(observation)
        if memory is not None:
            memory.append(observation)

        state = next_state
        if torch.all(done):
            break

    return trajectory


def rollout_actions(
    dynamical_model,
    reward_model,
    action_sequence,
    initial_state,
    termination_model=None,
    memory=None,
):
    """Conduct a rollout of an action sequence interacting with a model.

    Parameters
    ----------
    dynamical_model: AbstractModel
        Dynamical Model with which the policy interacts.
    reward_model: AbstractReward, optional.
        Reward Model with which the policy interacts.
    action_sequence: Action
        Action Sequence that interacts with the environment.
        The dimensions are [horizon x num samples x dim action].
    initial_state: State
        Starting states for the interaction.
        The dimensions are [1 x num samples x dim state].
    termination_model: Callable.
        Termination condition to finish the rollout.
    memory: ExperienceReplay, optional.
        Memory where to store the simulated transitions.

    Returns
    -------
    trajectory: Trajectory=List[Observation]
        A list of observations.

    Notes
    -----
    It will try to do the re-parametrization trick with the policy and models.
    """
    trajectory = list()
    state = initial_state
    done = torch.full(state.shape[:-1], False, dtype=torch.bool)

    for action in action_sequence:  # Normalized actions

        observation, next_state, done = step_model(
            dynamical_model=dynamical_model,
            reward_model=reward_model,
            termination_model=termination_model,
            state=state,
            action=action,
            action_scale=1.0,
            done=done,
        )
        trajectory.append(observation)
        if memory is not None:
            memory.append(observation)

        state = next_state
        if torch.all(done):
            break

    return trajectory
