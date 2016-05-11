"""
Handle storing and retrieving featured article

The FEATURED_TITLE can only be set via the UI when there's an available
persistent storage mechanism like Redis configured.  Otherwise the
FEATURED_TITLE is stored in an environment variable that cannot be set from the
UI.  We do not allow setting of the environment variable from the UI because
the application could be running on multiple instances so setting a single
environment variable will only affect a single instance.

You can use Heroku's admin panel or CLI to set environment variables for all
instances of your application, if you're running on Heroku without Redis.
"""

import os

from .. import PUBLISHED
from .. import cache
from . import get_available_articles

# Use ':' to help distinguish it from other things that could be in the cache.
# This is a bit of a hack but no need to create an entirely new redis database
# just for a single key, requires more setup from users.
CACHE_KEY = 'FEATURED_TITLE:'

# This is different than CACHE_KEY for backwards-compatible reasons only.
ENV_KEY = 'FEATURED_TITLE'


def allow_set_featured_article():
    """
    Return True or False if the ability to set the featured article is allowed
    from the UI.  If False, then the featured guide should be set via an
    environment variable called FEATURED_TITLE.
    """

    return cache.is_enabled()


def set_featured_article(title):
    """
    Set featured article

    :param title: Title of featured article
    """

    # None for timeout b/c this should never expire
    cache.save(CACHE_KEY, title, timeout=None)


def get_featured_article(articles=None):
    """
    Find featured article in list of articles or published articles

    :params articles: List of article objects to search for featured article or
                      use published articles if no list is given
    :returns: Article object of featured article or None if not found
    """

    featured = None
    if allow_set_featured_article():
        featured = cache.get(CACHE_KEY)

    if featured is None:
        featured = os.environ.get(ENV_KEY)

    if featured is None:
        return None

    if articles is None:
        # FIXME: This should only fetch the most recent x number.
        articles = list(get_available_articles(status=PUBLISHED))

    featured = featured.strip()

    for article in articles:
        # Don't allow surrounding spaces to mismatch
        if article.title.strip() == featured:
            return article

    return None
