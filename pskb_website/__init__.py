"""
Configure Flask app instance
"""

import logging
import os

from flask import Flask, url_for

# Possible publish statuses
DRAFT = u'draft'
IN_REVIEW = u'in-review'
PUBLISHED = u'published'

STATUSES = (PUBLISHED, IN_REVIEW, DRAFT)

SLACK_URL = u'https://hackguides.herokuapp.com'

app = Flask(__name__)

# Running on heroku
if 'HEROKU' in os.environ and os.environ['HEROKU'].lower() in ('true', 'yes', '1'):
    import example_config

    # example_config.py provides a blueprint for which variables to look for in
    # the environment and set in our app config.
    for var in example_config.HEROKU_ENV_REQUIREMENTS:
        try:
            value = os.environ[var]
        except KeyError:
            print 'Unable to find environment variable %s, defaulting to empty string' % (var)
            value = ''

        app.config.setdefault(var, value)

        if var == 'SECRET_KEY':
            app.secret_key = os.environ[var]

    if 'DEBUG' in os.environ:
        app.debug = True

        print 'Config values'
        for key, value in app.config.iteritems():
            print key, value

else:
    try:
        app.config.from_object(os.environ['APP_SETTINGS'])
    except KeyError:
        import example_config
        print 'Unable to find configuration, using example'
        app.config.from_object(example_config.DevelopmentConfig)

    app.secret_key = app.config['SECRET_KEY']

# Force flask to log to a file otherwise if we're not in DEBUG mode the logs
# won't show up in the console (on heroku)
if not app.debug:
    app.logger.setLevel(logging.INFO)
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s [in %(pathname)s:%(lineno)d]: %(message)s '))

    app.logger.addHandler(handler)


def url_for_domain(*args, **kwargs):
    """
    Wrapper for flask.url_for to allow for an external URL with a domain.  The
    point of this is to workaround the fact that setting
    app.config['SERVER_NAME'] creates external URLs for EVERY call to url_for.

    This function adds one extra kwarg called 'base_url'.  Using base_url with
    override the behavior of _external=True otherwise this function is a
    pass-through to flask.url_for().
    """

    base_url = kwargs.pop('base_url', None)
    if '_external' in kwargs and base_url:
        kwargs.pop('_external')

    url = url_for(*args, **kwargs)
    if base_url is not None:
        url = u'%s%s' % (base_url, url)

    return url


@app.context_processor
def context_processor():
    return dict(url_for_domain=url_for_domain)


import pskb_website.views
import pskb_website.api
import pskb_website.webhooks
import pskb_website.filters

app.jinja_env.filters['date_string'] = filters.date_string
app.jinja_env.filters['url_for_article'] = filters.url_for_article
app.jinja_env.filters['url_for_user'] = filters.url_for_user
app.jinja_env.filters['url_for_edit'] = filters.url_for_edit
app.jinja_env.filters['author_name'] = filters.author_name
