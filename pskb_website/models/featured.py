"""
Handle storing and retrieving featured article

The FEATURED_GUIDE can only be set via the UI when there's an available
persistent storage mechanism like Redis configured.  Otherwise the
FEATURED_GUIDE is stored in an environment variable that cannot be set from the
UI.  We do not allow setting of the environment variable from the UI because
the application could be running on multiple instances so setting a single
environment variable will only affect a single instance.

You can use Heroku's admin panel or CLI to set environment variables for all
instances of your application, if you're running on Heroku without Redis.
"""

import os
import json

from .. import PUBLISHED
from .. import cache
from . import get_available_articles

# Use ':' to help distinguish it from other things that could be in the cache.
# This is a bit of a hack but no need to create an entirely new redis database
# just for a single key, requires more setup from users.
CACHE_KEY = 'FEATURED_GUIDE:'
ENV_KEY = 'FEATURED_GUIDE'


def allow_set_featured_article():
    """
    Return True or False if the ability to set the featured article is allowed
    from the UI.  If False, then the featured guide should be set via an
    environment variable called FEATURED_GUIDE.
    """

    return cache.is_enabled()


def set_featured_article(article):
    """
    Set featured article

    :param article: Instance of models.article.Article to set as featured
    """

    value = (article.title, article.stacks[0])

    # None for timeout b/c this should never expire
    cache.save(CACHE_KEY, json.dumps(value), timeout=None)


def get_featured_article(articles=None):
    """
    Find featured article in list of articles or published articles

    :params articles: List of article objects to search for featured article or
                      use published articles if no list is given
    :returns: Article object of featured article or None if not found
    """

    title = None
    stack = None
    featured = None

    if allow_set_featured_article():
        featured = cache.get(CACHE_KEY)

    if featured is None:
        featured = os.environ.get(ENV_KEY)

    # Allow users to store only the title for backwards compatability
    if featured is not None:
        try:
            title, stack = json.loads(featured)
        except ValueError:
            title = featured

    if title is None:
        return None

    if articles is None:
        # FIXME: This should only fetch the most recent x number.
        articles = list(get_available_articles(status=PUBLISHED))

    title = title.strip()
    if stack is not None:
        stack = stack.strip().lower()

    for article in articles:
        # Don't allow surrounding spaces to mismatch
        if article.title.strip() == title:
            if stack is None or article.stacks[0].strip().lower() == stack:
                return article

    return None
