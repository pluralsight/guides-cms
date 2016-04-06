"""
Collection of shared functionality for models subpackage
"""

import collections
import copy
import json

from .. import remote
from .. import cache


def to_json(object_, exclude_attrs=None):
    """
    Return json representation of object

    :param exclude_attrs: List of attributes to exclude from serialization
    :returns: json representation of object as a string
    """

    if exclude_attrs is None:
        exclude_attrs = []

    # This is very simple by design. Assume we don't have a lot of crazy nested
    # data here so just do the bare minimum without over-engineering.
    dict_ = copy.deepcopy(object_.__dict__)
    for attr in exclude_attrs:
        del dict_[attr]

    # Print it to a string in a pretty format. Whitespace doesn't matter so
    # might as well make it more readable.
    return json.dumps(dict_, sort_keys=True, indent=4, separators=(',', ': '))


def contribution_stats():
    """
    Get total and weekly contribution stats for default repository

    :returns: Ordered dictionary keyed by author login name and ordered by most
              commits this week
              Each value in dictionary is a dictionary of stats for that
              contributor
    """

    cache_key = 'commit-stats'
    stats = cache.get(cache_key)
    if stats:
        return json.loads(stats)

    # Reformat data and toss out the extra, we're only worried about totals an
    # the current week.
    stats = []
    for user in remote.contributor_stats():
        # Assuming last entry is the current week to avoid having to calculate
        # timesteps, etc.
        this_week = user['weeks'][-1]

        stats.append({'avatar_url': user['author']['avatar_url'],
                      'login': user['author']['login'],
                      'total': user['total'],
                      'weekly_commits': this_week['c'],
                      'weekly_additions': this_week['a'],
                      'weekly_deletions': this_week['d']})

    if not stats:
        return {}

    ordered_stats = collections.OrderedDict()
    for user_dict in sorted(stats, key=lambda v: v['weekly_commits'],
                            reverse=True):
        login = user_dict.pop('login')
        ordered_stats[login] = user_dict

    # Just fetch stats every 30 minutes, this is not a critical bit of data
    cache.save(cache_key, json.dumps(ordered_stats), timeout=30 * 60)

    return ordered_stats
