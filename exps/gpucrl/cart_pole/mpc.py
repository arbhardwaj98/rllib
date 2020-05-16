from dotmap import DotMap

from exps.gpucrl.cart_pole import TRAIN_EPISODES, ENVIRONMENT_MAX_STEPS, ACTION_COST, \
    get_agent_and_environment
from exps.gpucrl.mpc_arguments import parser
from exps.gpucrl.plotters import plot_last_trajectory
from exps.gpucrl.util import train_and_evaluate

MPC_HORIZON, MPC_NUM_SAMPLES = 25, 400

parser.description = 'Run Swing-up Cart-Pole using Model-Based MPC.'
parser.set_defaults(action_cost=ACTION_COST,
                    train_episodes=TRAIN_EPISODES,
                    environment_max_steps=ENVIRONMENT_MAX_STEPS,
                    mpc_horizon=MPC_HORIZON,
                    mpc_num_samples=MPC_NUM_SAMPLES,
                    mpc_num_elites=MPC_NUM_SAMPLES // 10,
                    model_kind='DeterministicEnsemble',
                    model_learn_num_iter=50,
                    model_opt_lr=1e-3)

args = parser.parse_args()
params = DotMap(vars(args))

environment, agent = get_agent_and_environment(params, 'mpc')
train_and_evaluate(agent, environment, params=params,
                   plot_callbacks=[plot_last_trajectory])