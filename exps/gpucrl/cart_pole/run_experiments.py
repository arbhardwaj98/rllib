"""Run Cart-Pole experiments."""

from lsf_runner import make_commands, init_runner
from exps.gpucrl.cart_pole import ACTION_COST

for agent in ['mpc', 'mbmppo']:
    runner = init_runner(f'GPUCRL_CartPole_{agent}', num_threads=1)

    cmd_list = make_commands(
        f'{agent}.py',
        base_args={},
        fixed_hyper_args={},
        common_hyper_args={
            'exploration': ['thompson', 'optimistic', 'expected'],
            'model-kind': ['ProbabilisticEnsemble', 'DeterministicEnsemble'],
            'action-cost': [0, ACTION_COST, 5 * ACTION_COST],
        },
        algorithm_hyper_args={},
    )
    runner.run(cmd_list)