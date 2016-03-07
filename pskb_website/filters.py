"""
Misc. filter tags for templates
"""

from flask import url_for

from . import app
from . import utils


def date_string(dt, fmt_str):
    """
    Format dt object with given format string

    :param fmt_str: Format string to be used with datetime.datetime.strftime
    :returns: Date formatted as string
    """

    return dt.strftime(fmt_str)


def url_for_article(article, base_url=app.config['BASE_URL'], branch=u'master'):
    """
    Get URL for article object

    :param article: Article object
    :returns: URL as string

    Note this filter is directly linked to the views.review URL.  These must be
    changed together!

    This filter only exists to centralize the ability to create a url for an
    article so we can store the url in a file or render in templates.
    """

    title = utils.slugify(article.title)
    stack = utils.slugify_stack(article.stacks[0])

    # The '-' is better for URL SEO but '_' is better for a function name
    status = article.publish_status.replace('-', '_')

    url = u'%s%s' % (base_url, url_for(status, title=title, stack=stack))

    if branch != u'master':
        url = u'%s?branch=%s' % (branch)

    return url


def url_for_user(user):
    """
    Get URL for user object

    :param user: User object or username
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

    return u'%s%s' % (app.config['BASE_URL'],
                      url_for('user_profile', author_name=username))

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
