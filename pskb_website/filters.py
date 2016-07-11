"""
Misc. filter tags for templates
"""

from urllib import urlencode

from flask import url_for

from . import PUBLISHED
from . import app
from . import utils


def date_string(dt, fmt_str):
    """
    Format dt object with given format string

    :param fmt_str: Format string to be used with datetime.datetime.strftime
    :returns: Date formatted as string
    """

    return dt.strftime(fmt_str)


def url_for_edit(article, **kwargs):
    """
    Get URL to edit article

    :param article: Article object
    :param kwargs: Passed directly into flask.url_for
    :returns: URL as string
    """

    title = utils.slugify(article.title)
    stack = utils.slugify_stack(article.stacks[0])

    return url_for(u'write', title=title, stack=stack, **kwargs)


def url_for_article(article, base_url=None, branch=u'master', **kwargs):
    """
    Get URL for article object

    :param article: Article object
    :param base_url: Base URL i.e domain, etc. to use
    :param branch: Branch
    :param kwargs: Passed directly into flask.url_for
    :returns: URL as string

    Note this filter is directly linked to the views.article_view URL.  These
    must be changed together!

    Also note the branch argument is optional even though it's included in the
    article object.  This is for extra flexibility so callers can generate urls
    for several branches without having to read that branch specifically and
    creating an article object.

    This filter only exists to centralize the ability to create a url for an
    article so we can store the url in a file or render in templates.
    """

    title = utils.slugify(article.title)
    stack = utils.slugify_stack(article.stacks[0])

    url = url_for(u'article_view', title=title, stack=stack, **kwargs)

    if base_url is not None:
        url = u'%s%s' % (base_url, url)

    if article.publish_status != PUBLISHED:
        query_str_arg = '&' if '?' in url else '?'
        url = u'%s%sstatus=%s' % (url, query_str_arg, article.publish_status)

    if branch != u'master':
        query_str_arg = '&' if '?' in url else '?'
        # Must encode branch name b/c it could have special characters like '+'
        # for stacks like c++
        url = u'%s%s%s' % (url, query_str_arg, urlencode({'branch': branch}))

    return url


def url_for_user(user, base_url=None):
    """
    Get URL for user object

    :param user: User object or username
    :param base_url: Base URL i.e domain, etc. to use
    :returns: URL as string

    Note this filter is directly linked to the views.user_profile URL.  These
    must be changed together!

    This filter only exists to centralize the ability to create a url for an
    user so we can store the url in a file or render in templates.
    """

    try:
        username = user.login
    except AttributeError:
        username = user

    url = url_for('user_profile', author_name=username)
    if base_url is not None:
        url = u'%s%s' % (base_url, url)

    return url


def author_name(article):
    """
    Get best available name for author, preferring real name

    :param article: Article object
    :returns: Author name as string
    """

    if not article:
        return ''

    if article.author_real_name:
        return article.author_real_name

    return article.author_name
