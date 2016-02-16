"""
Collection of shared functionality for models subpackage
"""

import copy
import json


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
