"""
Module to manage CRUD operations on saving contributor information
"""

from .. import app
from .. import utils

redis_obj = None

url = app.config.get('REDIS_CONTRIBUTOR_DB_URL')

if not url:
    url = app.config.get('REDISCLOUD_URL')
    app.logger.debug('Attempting to store hearts with REDISCLOUD_URL')
else:
    app.logger.debug('Attempting to store hearts with REDIS_CONTRIBUTOR_DB_URL')

if not url:
    app.logger.warning('No users will be saved, please set REDIS_CONTRIBUTOR_DB_URL or REDISCLOUD_URL environment variable to enable persistent user information.')
else:
    redis_obj = utils.configure_redis_from_url(url)
    if redis_obj is None:
        app.logger.warning('No users will be saved, unable to configure redis')


def update_info(username, email):
    """
    Update contributor information

    :param username: String of username
    :param email: email
    """

    if redis_obj is None:
        return

    redis_obj.set('user:%s' % (username), email)


def get_info(username):
    """
    Get contributor information

    :param username: String of username
    :returns: Data stored for that username
    """

    if redis_obj is None:
        return

    return redis_obj.get('user:%s' % (username))
