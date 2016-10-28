"""
Generic functions for global use
"""

from datetime import datetime
import re
from unicodedata import normalize
import urlparse

from . import app

_punct_re = re.compile(r'[\t !"#$%&\'()*\-/<=>?@\[\\\]^_`{|},.:]+')


# From http://flask.pocoo.org/snippets/5/
def slugify(text, delim=u'-'):
    """Generates an slightly worse ASCII-only slug."""

    result = []

    for word in _punct_re.split(text.lower()):
        word = normalize('NFKD', word).encode('ascii', 'ignore')
        if word:
            result.append(word)

    return unicode(delim.join(result))


def slugify_stack(stack):
    """Generates an ASCII-only slug version of the stack"""

    # Just take anything before the '('. Some of our stacks are really long and
    # would make for ugly URLs and folders.
    return slugify(stack.split('(')[0])


def configure_redis_from_url(url):
    """
    Create and configure a redis instance from the given url

    :param url: URL encoded in the popular `scheme://netloc/path;parameters?query#fragment` that urlparse.urlparse supports
    :returns: configured redis.Redis object or None if there was a problem
    """

    try:
        import redis
    except ImportError:
        app.logger.error('Redis module not installed')
        return None

    try:
        url = urlparse.urlparse(url)
    except Exception as err:
        app.logger.error('Failed parsing redis URL: "%s", err: %s', url, err)
        app.logger.debug('Trace:', exc_info=True)
        return None

    try:
        return redis.Redis(host=url.hostname, port=url.port, password=url.password)
    except Exception as err:
        app.logger.error('Failed creating redis instance: err: %s', err)
        app.logger.debug('Trace:', exc_info=True)
        return None


def datetime_from_utc_string(utc_time):
    """
    Parse UTC +00 string into datetime object

    :returns: Datetime object
    """

    # Note we're assuming UTC offset 0 ('Z') as the format!
    return datetime.strptime(utc_time, "%Y-%m-%dT%H:%M:%SZ")
