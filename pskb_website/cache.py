"""
Caching utilities

There are some quirks to be aware of when caching in this system.  Typically
you wouldn't want to set a timeout on the cache key and instead just flush it
from cache when things changed.  We cannot do this because we can get changes
from 2 places, the website application and github.com.  So, anything that can
change on github.com should have a reasonable cache timeout.  This way even if
our application doesn't see it change we will refresh from github periodically
just in case it changed there too.

Note that all errors are logged but not raised outside of this module.  The
cache is considered optional so we should allow the application to run
regardless.

Alot of the following functions are simple wrappers to provide a clean API
naming scheme to the outside world.  We could also expose our get/save wrappers
if we wanted to.  However, we're trying to hide the fact that we use redis so
we could easily switch later without other layers needing changes.

In addition, this layer knows how to turn arguments into cache keys.

Note we can use the same database for caching and models.heart data so you
should be careful to never clash keys unless you set the REDIS_HEARTS_DB_URL
environment variable to another database than this module uses!
"""

import functools

from . import app
from . import utils

# 8 minutes
DEFAULT_CACHE_TIMEOUT = 8 * 60

redis_obj = None

try:
    url = app.config['REDISCLOUD_URL']
except KeyError:
    app.logger.warning('No caching available, please set REDISCLOUD_URL environment variable to enable caching.')
else:
    if not url:
        app.logger.warning('No caching available, empty REDISCLOUD_URL')
    else:
        redis_obj = utils.configure_redis_from_url(url)
        if redis_obj is None:
            app.logger.warning('No caching available, missing redis module')


# Local cache of etags from API requests for file listing. Saving these here
# b/c they are small and can be kept in RAM without having to do http request
# to redis.
# Keyed by (repo, sha, filename)
FILE_LISTING_ETAGS = {}


def is_enabled():
    """
    Determine if cache is enabled or not
    :returns: True or False
    """

    return redis_obj is not None


def verify_redis_instance(func):
    """
    Decorator to verify redis instance exists and return None if missing redis
    """

    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        if not is_enabled():
            return False

        return func(*args, **kwargs)

    return _wrapper


@verify_redis_instance
def save(key, value, timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Generic function to save a key/value pair

    :param key: Key to save
    :param value: Value to save
    :param timeout: Timeout in seconds to cache text, use None for no timeout
    :returns: True or False if save succeeded, irrespective of setting the
              timeout
    """

    try:
        redis_obj.set(key, value)
    except Exception:
        app.logger.warning('Failed saving key "%s" to cache:', key,
                           exc_info=True)
        return False

    if timeout is not None:
        try:
            redis_obj.expire(key, timeout)
        except Exception:
            app.logger.warning('Failed setting key "%s", timeout: %d expiration in cache:',
                               key, timeout, exc_info=True)

    return True


@verify_redis_instance
def get(key):
    """
    Look for cached value with given key

    :param key: Key data was cached with
    :returns: Value saved or None if not found or error
    """

    if redis_obj is None:
        return None

    try:
        return redis_obj.get(key)
    except Exception:
        app.logger.warning('Failed reading key "%s" from cache:', key,
                           exc_info=True)
        return None


def read_file(path, branch):
    """
    Look for text pointed to by given path and branch in cache

    :param path: Short path to file not including repo information
    :param branch: Name of branch file belongs to
    :returns: Text saved to cache or None if not found
    """

    return get((path, branch))


def save_file(path, branch, text, timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Save file text in cache

    :param path: Short path to file not including repo information
    :param branch: Name of branch file belongs to
    :param text: Raw text to save
    :param timeout: Timeout in seconds to cache text, use None for no timeout
    :returns: True or False if save succeeded
    """

    return save((path, branch), text, timeout=timeout)


@verify_redis_instance
def delete_file(path, branch):
    """
    Delete file from cache

    :param path: Short path to file not including repo information
    :param branch: Name of branch file belongs to
    :returns: None
    """

    redis_obj.delete((path, branch))


def save_user(username, user, timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Save user JSON in cache

    :param username: Username for user
    :param user: Serialized representation of user to store in cache
    :returns: True or False if save succeeded
    """

    return save(username, user, timeout=timeout)


def read_user(username):
    """
    Read user from cache

    :param username: Username for user
    :returns: Serialized representation of user object or None if not found
    """

    return get(username)


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


def read_file_listing(key):
    """
    Read list of files from cache

    :param key: Key to read listing with
    :returns: Iterable of files
    """

    return get(key)


def save_file_listing(key, files, timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Save list of files to cache

    :param key: Key to save listing with
    :param files: Iterable of files
    :param timeout: Timeout in seconds to cache list, use None for no
                    timeout
    :returns: True or False if save succeeded
    """

    return save(key, files, timeout=timeout)
