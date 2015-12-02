"""
Caching utilities
"""

import collections
import os
import pickle
import urlparse
import json

from . import app

url = None
redis_obj = None

try:
    import redis
except ImportError:
    app.logger.warning('No caching available, missing redis module')
else:
    try:
        url = urlparse.urlparse(app.config['REDISCLOUD_URL'])
    except KeyError:
        app.logger.warning('No caching available, missing REDISCLOUD_URL env var')
    else:
        redis_obj = redis.Redis(host=url.hostname, port=url.port,
                                password=url.password)


def read_article(path, branch):
    """
    Look for article pointed to by given path and branch in cache

    :param path: Short path to article not including repo information
    :param branch: Name of branch article belongs to
    :returns: JSON representation of article or None if not found in cache
    """

    if redis_obj is None:
        return None

    return redis_obj.get((path, branch))


def save_article(article):
    """
    Save article JSON in cache

    :param article: model.article.Article object
    :returns: None
    """

    if redis_obj is None:
        return

    redis_obj.set((article.path, article.branch), article.to_json())
