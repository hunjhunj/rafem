#! /usr/local/bin/python

import steep_desc
import downcut
import FP
import numpy as np
import math
import pudb

from avulsion_utils import (find_point_in_path, channel_is_superelevated,
                            find_path_length, find_riv_path_length,
                            set_linear_slope, fill_abandoned_channel)


def avulse_to_new_path(z, old, new, sea_level, channel_depth, avulsion_type,
                       slope, dx=1., dy=1.,):
    """Avulse the river to a new path.

    Given two river paths, *old* and *new*, avulse the river to a new river
    path. If the end point of the new path is contained in the old river
    path, the resulting path is the new path up until this point and then
    the old path. Otherwise, the resulting path is the new river path and
    will be downcut.

    Parameters
    ----------
    z : ndarray
        2D array of elevations.
    old : tuple of array_like
        Tuple of i and j indices (into *z*) for the old path.
    new : tuple of array_like
        Tuple of i and j indices (into *z*) for the new path.
    sea_level : float
        Elevation of sea level.
    channel_depth : float
        Depth of the channel.
    avulsion_type : {0, 1, 2, 3}
        The type of the avulsion.
    dx : float, optional
        Spacing of columns of *z*.
    dy : float, optional
        Spacing of rows of *z*.

    Returns
    -------
    tuple
        Tuple of the new river path (as i, j indices) and the, possibly
        changed, avulsion type.

    Examples
    --------
    The following example uses a grid that looks like::

        o  +  *  *
        *  o  +  *
        *  *  +  *
        *  *  o  *
        *  o  *  *
    
    The old path is marked by `o`, the new path but `+`. The paths overlap
    (2, 2).

    >>> import numpy as np
    >>> z = np.ones((5, 4), dtype=float)

    >>> old = np.array((0, 1, 2, 3, 4)), np.array((0, 1, 2, 2, 1))
    >>> new = np.array((0, 1, 2)), np.array((1, 2, 2))
    >>> (new, atype) = avulse_to_new_path(z, old, new, 0., 0., 0)

    The new path follows the new path until the common point and then
    follows the old path. The new avulsion type is now 2.

    >>> new
    (array([0, 1, 2, 3, 4]), array([1, 2, 2, 2, 1]))
    >>> atype
    2

    In this example the old and new paths do not overlap::

        o  +  *  *
        *  o  +  *
        *  *  o  +
        *  *  o  +
        *  o  *  +

    >>> old = np.array((0, 1, 2, 3, 4)), np.array((0, 1, 2, 2, 1))
    >>> new = np.array((0, 1, 2, 3, 4)), np.array((1, 2, 3, 3, 3))
    >>> (new, atype) = avulse_to_new_path(z, old, new, 0., 0., 0)

    The new path is now, in fact, the actual new path and the avulsion
    type is unchanged.

    >>> new
    (array([0, 1, 2, 3, 4]), array([1, 2, 3, 3, 3]))
    >>> atype
    0
    """
    old_i, old_j = old
    new_i, new_j = new
    # sets avulsion to be regional, may be updated again below (if local)
            
    # maybe this should be len(test_old_x)-1?
    ind = find_point_in_path((old_i, old_j), (new_i[-1], new_j[-1]))

    if ind is not None:
        avulsion_type = 2

        downcut.cut_local(new_i, new_j, z, dx=dx, dy=dy)

        new_i = np.append(new_i, old_i[ind + 1:])
        new_j = np.append(new_j, old_j[ind + 1:])
    else:
        max_cell_h = slope * dx
        if (z[new_i[-1], new_j[-1]] - sea_level) < (0.001 * max_cell_h):
            z[new_i[-1], new_j[-1]] = (0.001 * max_cell_h) + sea_level
        
        downcut.cut_new(new_i, new_j, z, sea_level, channel_depth,
                        dx=dx, dy=dy)

    return (new_i, new_j), avulsion_type


# determines if there is an avulsion along river course
def find_avulsion(riv_i, riv_j, n, super_ratio, current_SL, ch_depth,
                  short_path, splay_type, splay_dep, slope, splay_depth, 
                  dx=1., dy=1.):
    new = riv_i, riv_j
    old = riv_i, riv_j
    avulsion_type = 0
    a = 0
    avulse_length = 0
    new_length = 0
    old_length = 0
    new_course_length = 0
    old_course_length = 0
    avul_locs = np.zeros(0, dtype=np.int)
    path_slopes = np.zeros(0)
    crevasse_locs = np.zeros(2, dtype=np.int)


    for a in xrange(1, len(riv_i)-1):
        if channel_is_superelevated(n, (riv_i[a], riv_j[a]),
                                    (riv_i[a-1], riv_j[a-1]),
                                    ch_depth, super_ratio, current_SL):
            pu.db

            # if superelevation greater than trigger ratio, determine
            # new steepest descent path
            new = steep_desc.find_course(n, riv_i, riv_j, a, ch_depth,
                                         sea_level=current_SL)

            if n[new[0][-1], new[1][-1]] < current_SL:
                new_length = find_riv_path_length(n, (new[0][a:], new[1][a:]),
                                                  current_SL, ch_depth,
                                                  slope, dx=dx, dy=dy)
            else:
                new_length = find_path_length(n, (new[0][a:], new[1][a:]),
                                              current_SL, ch_depth,
                                              slope, dx=dx, dy=dy)

            old_length = find_riv_path_length(n, (old[0][a:], old[1][a:]),
                                              current_SL, ch_depth,
                                              slope, dx=dx, dy=dy)

            if new_length < old_length:
                # calculate slope of new path
                slope = ((n[new[0][a], new[1][a]] - n[new[0][-1], new[1][-1]])
                         / new_length)

                avul_locs = np.append(avul_locs, a)
                path_slopes = np.append(path_slopes, slope)

            crevasse_locs = np.vstack((crevasse_locs, [new[0][a], new[0][a]]))


    if len(crevasse_locs.shape) > 1:
        crevasse_locs = np.delete(crevasse_locs, 0, 0)

    if avul_locs:

        max_slope = np.argmax(path_slopes)
        a = avul_locs[max_slope]

        new = steep_desc.find_course(n, riv_i, riv_j, a, ch_depth,
                                     sea_level=current_SL)

        avulsion_type = 1

        new, avulsion_type = avulse_to_new_path(n,
                                 (riv_i[a - 1:], riv_j[a - 1:]),
                                 (new[0][a - 1:], new[1][a - 1:]),
                                 current_SL, ch_depth, avulsion_type,
                                 slope, dx=dx, dy=dy)

        new = (np.append(riv_i[:a - 1], new[0]),
               np.append(riv_j[:a - 1], new[1]))

        # fill up old channel... could be some fraction in the future
        # (determines whether channels are repellors or attractors)
        fill_abandoned_channel(a, n, new, riv_i, riv_j, current_SL,
                               ch_depth, slope, dx)
        
        avulse_length = find_riv_path_length(n, (riv_i[a:], riv_j[a:]),
                                             current_SL, ch_depth,
                                             slope, dx=dx, dy=dy)

        old_course_length = find_riv_path_length(n, old, current_SL, ch_depth,
                                      slope, dx=dx, dy=dy)
        new_course_length = find_riv_path_length(n, new, current_SL, ch_depth,
                                      slope, dx=dx, dy=dy)

        crevasse_locs = np.delete(crevasse_locs, max_slope, 0)

    else:
        new = riv_i, riv_j

    if (crevasse_locs.sum() > 0) and (splay_type > 0):

        n_before_splay = np.copy(n)

        old_river_elevations = n[riv_i, riv_j]
        new_river_elevations = n[new[0], new[1]]

        for i in xrange(crevasse_locs.shape[0]):
            FP.dep_splay(n, (crevasse_locs[i][0], crevasse_locs[i][1]),
                         splay_dep, splay_type=splay_type)

        n[riv_i, riv_j] = old_river_elevations
        n[new[0], new[1]] = new_river_elevations
        n_splay = n - n_before_splay
        splay_depth += n_splay

    return (new, avulsion_type, a, avulse_length, (old_course_length - new_course_length), splay_depth)
