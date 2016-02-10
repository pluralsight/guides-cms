"""
Misc. filter tags for templates
"""

from flask import url_for

from . import app


def date_string(dt, fmt_str):
    """
    Format dt object with given format string

    :param fmt_str: Format string to be used with datetime.datetime.strftime
    :returns: Date formatted as string
    """

    return dt.strftime(fmt_str)


def url_for_article(article):
    """
    Get URL for article object

    :param article: Article object
    :returns: URL as string

    Note this filter is directly linked to the views.review URL.  These must be
    changed together!

    This filter only exists to centralize the ability to create a url for an
    article so we can store the url in a file or render in templates.
    """

    return '%s%s' % (app.config['BASE_URL'],
                      url_for('review', article_path=article.path))


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

    return '%s%s' % (app.config['BASE_URL'],
                      url_for('user_profile', author_name=username))
