"""
Module to manage CRUD operations on 'heart'ing guides
"""

from .. import app
from .. import utils

redis_obj = None


try:
    url = app.config['REDISCLOUD_URL']
except KeyError:
    app.logger.warning('No hearts will be saved, please verify REDISCLOUD_URL environment variable to enable persistent hearting of guides.')
else:
    redis_obj = utils.configure_redis_from_url(url)
    if redis_obj is None:
        app.logger.warning('No hearts will be saved, please verify REDISCLOUD_URL environment variable to enable persistent hearting of guides.')


def _generate_key(stack, title):
    """
    Generate a key for hearts operation
    """

    # Note we're using a ':' here in the key which is very important because we
    # do not allow this character in a stack or title. Thus, this ensures the
    # keys for hearts don't clash with other things. This allows us to use the
    # same redis database for hearts and caching.
    return 'heart:%s:%s' % (utils.slugify_stack(stack.lower()),
                            utils.slugify(title))


def add_heart(stack, title, username):
    """
    Add heart to stack/title pair for given username

    :param stack: String of stack of article
    :param title: String of title of article
    :param username: String of user adding heart
    :returns: New count after adding heart

    Note a user can only heart a stack/title pair once so multiple calls to
    this will not make any change i.e. will not add additional hearts.
    """

    if redis_obj is None:
        return 0

    redis_obj.sadd(_generate_key(stack, title), username)
    return count_hearts(stack, title)


def remove_heart(stack, title, username):
    """
    Remove heart from stack/title pair for given username

    :param stack: String of stack of article
    :param title: String of title of article
    :param username: String of user removing heart
    :returns: New count after removing heart

    Note a user can only heart a stack/title pair once so multiple calls to
    this will not make any change i.e. will not remove additional hearts.
    """

    if redis_obj is None:
        return 0

    redis_obj.srem(_generate_key(stack, title), username)
    return count_hearts(stack, title)


def count_hearts(stack, title):
    """
    Get number of hearts for stack/title pair

    :param stack: String of stack of article
    :param title: String of title of article
    :returns: Number of hearts
    """

    if redis_obj is None:
        return 0

    return redis_obj.scard(_generate_key(stack, title))


def has_hearted(stack, title, username):
    """
    Determine if given user has hearted an article

    :param stack: String of stack of article
    :param title: String of title of article
    :returns: True or False
    """

    if redis_obj is None:
        return False

    return redis_obj.sismember(_generate_key(stack, title), username)
