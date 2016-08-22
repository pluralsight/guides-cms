"""
Collection of shared functionality for models subpackage
"""

import collections
import copy
import json

from .. import app
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

    def _sort_contributions(stats):
        ordered_stats = collections.OrderedDict()
        for user_dict in sorted(stats, key=lambda v: v['weekly_commits'],
                                reverse=True):
            login = user_dict.pop('login')
            ordered_stats[login] = user_dict

        return ordered_stats

    cache_key = 'commit-stats'
    stats = cache.get(cache_key)
    if stats:
        return _sort_contributions(json.loads(stats))

    # Reformat data and toss out the extra, we're only worried about totals an
    # the current week.
    stats = []
    for user in remote.contributor_stats():
        # Assuming last entry is the current week to avoid having to calculate
        # timesteps, etc.
        this_week = user['weeks'][-1]
        if this_week is None:
            app.logger.warning('Weeks contribution info is None: %s', user)
            continue

        author = user['author']
        if author is None:
            app.logger.warning('Author contribution info is None: %s', user)
            continue

        stats.append({'avatar_url': author['avatar_url'],
                      'login': author['login'],
                      'total': user['total'],
                      'weekly_commits': this_week['c'],
                      'weekly_additions': this_week['a'],
                      'weekly_deletions': this_week['d']})

    if not stats:
        return {}

    # Note we do NOT cache the ordered results b/c we use an ordered dict for
    # that and we cannot serialize an ordered dict and maintain insert order.

    # Just fetch stats every 30 minutes, this is not a critical bit of data
    cache.save(cache_key, json.dumps(stats), timeout=30 * 60)

    return _sort_contributions(stats)


def contributors_to_ignore():
    """
    Get set of logins to ignore from all contribution stats

    :returns: Set of logins
    """

    users = set([])
    for user in app.config.get('IGNORE_STATS_FOR', '').split(','):
        users.add(user.strip())

    return users
