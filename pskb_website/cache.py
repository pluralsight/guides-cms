"""
Caching utilities
"""

import functools
import urlparse

from . import app

# 30 minutes
DEFAULT_CACHE_TIMEOUT = 30 * 60

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
        app.logger.warning('No caching available, missing REDISCLOUD_URL env var')
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
def read_article(path, branch):
    """
    Look for article pointed to by given path and branch in cache

    :param path: Short path to article not including repo information
    :param branch: Name of branch article belongs to
    :returns: JSON representation of article or None if not found in cache
    """

    return redis_obj.get((path, branch))


@verify_redis_instance
def save_article(path, branch, article, timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Save article JSON in cache

    :param path: Short path to article not including repo information
    :param branch: Name of branch article belongs to
    :param article: Serialized representation of article to store in cache
    :param timeout: Timeout in seconds to cache article, use None for no
                    timeout
    :returns: None
    """

    key = (path, branch)
    redis_obj.set(key, article)

    if timeout is not None:
        redis_obj.expire(key, timeout)


@verify_redis_instance
def delete_article(article):
    """
    Delete article from cache

    :param article: model.article.Article object
    :returns: None
    """

    redis_obj.delete((article.path, article.branch))


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

    :param key: (repo, sha, filename)
    :returns: Iterable of files

    The key should be the same one used to save etag with
    :func:`.save_file_listing_etag`.
    """

    return redis_obj.get(key)


@verify_redis_instance
def save_file_listing(key, files, timeout=DEFAULT_CACHE_TIMEOUT):
    """
    Save list of files to cache

    :param key: (repo, sha, filename)
    :param files: Iterable of files
    :param timeout: Timeout in seconds to cache list, use None for no
                    timeout
    :returns: None

    The key should be the same one used to save etag with
    :func:`.save_file_listing_etag`.
    """

    redis_obj.set(key, files)

    if timeout is not None:
        redis_obj.expire(key, timeout)
