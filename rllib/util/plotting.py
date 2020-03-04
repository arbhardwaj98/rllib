"""Python Script Template."""
import numpy as np
import torch
import itertools
import matplotlib.pyplot as plt
from rllib.util import moving_average_filter

__all__ = ['combinations', 'linearly_spaced_combinations', 'plot_combinations_as_grid',
           'plot_learning_losses', 'plot_on_grid', 'plot_values_and_policy']


def combinations(arrays):
    """Return a single array with combinations of parameters.

    Parameters
    ----------
    arrays : list of np.array

    Returns
    -------
    array : np.array
        An array that contains all combinations of the input arrays
    """
    return np.array(np.meshgrid(*arrays)).T.reshape(-1, len(arrays))


def linearly_spaced_combinations(bounds, num_entries):
    """
    Return 2-D array with all linearly spaced combinations with the bounds.

    Parameters
    ----------
    bounds : sequence of tuples
        The bounds for the variables, [(x1_min, x1_max), (x2_min, x2_max), ...]
    num_entries : integer or array_like
        Number of samples to use for every dimension. Can be a constant if
        the same number should be used for all, or an array to fine-tune
        precision. Total number of data points is num_samples ** len(bounds).

    Returns
    -------
    combinations : 2-d array
        A 2-d arrray. If d = len(bounds) and l = prod(num_samples) then it
        is of size l x d, that is, every row contains one combination of
        inputs.
    """
    bounds = np.atleast_2d(bounds)
    num_vars = len(bounds)
    num_entries = np.broadcast_to(num_entries, num_vars)

    # Create linearly spaced test inputs
    inputs = [np.linspace(b[0], b[1], n) for b, n in zip(bounds,
                                                         num_entries)]

    # Convert to 2-D array
    return combinations(inputs)


def plot_combinations_as_grid(axis, values, num_entries, bounds=None, **kwargs):
    """Take values from a grid and plot them as an image.

    Takes values generated from `linearly_spaced_combinations`.

    Parameters
    ----------
    axis : matplotlib.axis
    values : ndarray
    num_entries : array_like
        Number of samples to use for every dimension.
        Used for reshaping
    bounds : sequence of tuples
        The bounds for the variables, [(x1_min, x1_max), (x2_min, x2_max), ...]
    kwargs : dict
        Passed to axis.imshow
    """
    kwargs['origin'] = 'lower'
    if bounds is not None:
        kwargs['extent'] = list(itertools.chain(*bounds))

    return axis.imshow(values.reshape(*num_entries).T, **kwargs)


def plot_learning_losses(policy_losses, value_losses, horizon):
    """Plot the losses encountnered during learning.

    Parameters
    ----------
    policy_losses : list or ndarray
    value_losses : list or ndarray
    horizon : int
        Horizon used for smoothing
    """
    t = np.arange(len(policy_losses))

    fig, (ax1, ax2) = plt.subplots(ncols=2, figsize=(15, 5))

    plt.sca(ax1)
    plt.plot(t, policy_losses)
    plt.plot(*moving_average_filter(t, policy_losses, horizon),
             label='smoothed')
    plt.xlabel('Iteration')
    plt.ylabel('Policy loss')
    plt.legend()

    plt.sca(ax2)
    plt.plot(t, value_losses)
    plt.plot(*moving_average_filter(t, value_losses, horizon),
             label='smoothed')
    plt.xlabel('Iteration')
    plt.ylabel('Value loss')
    plt.legend()


def plot_on_grid(function, bounds, num_entries):
    """Plot function values on a grid.

    Parameters
    ----------
    function : callable
    bounds : list
    num_entries : list

    Returns
    -------
    axis
    """
    axis = plt.gca()
    states = linearly_spaced_combinations(bounds, num_entries)
    values = function(torch.from_numpy(states).float())
    values = values.detach().numpy()

    img = plot_combinations_as_grid(axis, values, num_entries, bounds)
    plt.colorbar(img)
    axis.set_xlim(bounds[0])
    axis.set_ylim(bounds[1])
    return axis


def plot_values_and_policy(value_function, policy, bounds, num_entries):
    """Plot the value and policy function over a grid.

    Parameters
    ----------
    value_function : torch.nn.Module
    policy : torch.nn.Module
    bounds : list
    num_entries : list

    Returns
    -------
    ax_value
    ax_policy
    """
    fig, (ax1, ax2) = plt.subplots(nrows=2, sharex=True, figsize=(15, 10))

    plt.sca(ax1)
    plot_on_grid(value_function, bounds=bounds, num_entries=num_entries)
    plt.title('Learned value function')
    plt.xlabel('Angle[rad]')
    plt.ylabel('Angular velocity [rad/s]')
    plt.axis('tight')

    plt.sca(ax2)
    plot_on_grid(lambda x: policy(x).mean, bounds=bounds, num_entries=num_entries)
    plt.title('Learned policy')
    plt.xlabel('Angle [rad]')
    plt.ylabel('Angular velocity [rad/s]')
    plt.axis('tight')

    return ax1, ax2