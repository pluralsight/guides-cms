"""
Caching utilities
"""

import functools
import urlparse

from . import app

# 8 minutes
DEFAULT_CACHE_TIMEOUT = 8 * 60

url = None
redis_obj = None

try:
    import redis
except ImportError:
    app.logger.warning('No caching available, missing redis module')
else:
    try:
        url = app.config['REDISCLOUD_URL']
    except KeyError:
        url = None

    if url is None:
        app.logger.warning('No caching available, please set REDISCLOUD_URL environment variable to enable caching.')
    else:
        url = urlparse.urlparse(app.config['REDISCLOUD_URL'])
        redis_obj = redis.Redis(host=url.hostname, port=url.port,
                                password=url.password)

# Local cache of etags from API requests for file listing. Saving these here
# b/c they are small and can be kept in RAM without having to do http request
# to redis.
# Keyed by (repo, sha, filename)
FILE_LISTING_ETAGS = {}


def verify_redis_instance(func):
    """
    Decorator to verify redis instance exists and return None if missing redis
    """

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        if redis_obj is None:
            return None

        return func(*args, **kwargs)

    return _wrapper


@verify_redis_instance
def read_file(path, branch):
    """
    Look for text pointed to by given path and branch in cache

    :param path: Short path to file not including repo information
    :param branch: Name of branch file belongs to
    :returns: Text saved to cache or None if not found
    """

    return redis_obj.get((path, branch))


@verify_redis_instance
def save_file(path, branch, text, timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Save file text in cache

    :param path: Short path to file not including repo information
    :param branch: Name of branch file belongs to
    :param text: Raw text to save
    :param timeout: Timeout in seconds to cache text, use None for no timeout
    :returns: None
    """

    key = (path, branch)
    redis_obj.set(key, text)

    if timeout is not None:
        redis_obj.expire(key, timeout)


@verify_redis_instance
def delete_file(path, branch):
    """
    Delete file from cache

    :param path: Short path to file not including repo information
    :param branch: Name of branch file belongs to
    :returns: None
    """

    redis_obj.delete((path, branch))


@verify_redis_instance
def save_user(username, user, timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Save user JSON in cache

    :param username: Username for user
    :param user: Serialized representation of user to store in cache
    :returns: None
    """

    redis_obj.set(username, user)

    if timeout is not None:
        redis_obj.expire(username, timeout)


@verify_redis_instance
def read_user(username):
    """
    Read user from cache

    :param username: Username for user
    :returns: Serialized representation of user object or None if not found
    """

    return redis_obj.get(username)


# These getter/setters only exist so we can move the cache location of these
# items transparently of the other layers.

def read_file_listing_etag(key):
    """
    Read etag from cache to do a file listing conditional API request

    :param key: (repo, sha, filename)
    :returns: etag from cache or None if no etag found
    """

    try:
        return FILE_LISTING_ETAGS[key]
    except KeyError:
        return None


def save_file_listing_etag(key, etag):
    """
    :param key: (repo, sha, filename)
    :param etag: etag as returned by API request header
    :returns: None
    """

    FILE_LISTING_ETAGS[key] = etag


@verify_redis_instance
def read_file_listing(key):
    """
    Read list of files from cache

    :param key: Key to read listing with
    :returns: Iterable of files
    """

    return redis_obj.get(key)


@verify_redis_instance
def save_file_listing(key, files, timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Save list of files to cache

    :param key: Key to save listing with
    :param files: Iterable of files
    :param timeout: Timeout in seconds to cache list, use None for no
                    timeout
    :returns: None
    """

    redis_obj.set(key, files)

    if timeout is not None:
        redis_obj.expire(key, timeout)
