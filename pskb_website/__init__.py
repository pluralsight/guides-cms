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


import pskb_website.views
import pskb_website.api
import pskb_website.webhooks
import pskb_website.filters

app.jinja_env.filters['date_string'] = filters.date_string
app.jinja_env.filters['url_for_article'] = filters.url_for_article
app.jinja_env.filters['url_for_user'] = filters.url_for_user
app.jinja_env.filters['url_for_edit'] = filters.url_for_edit
app.jinja_env.filters['author_name'] = filters.author_name


# Allow us to host the app on subdomain as well as a subfolder.
class ReverseProxied(object):
    """
    From: http://flask.pocoo.org/snippets/35/

    Wrap the application in this middleware and configure the
    front-end server to add these headers, to let you quietly bind
    this to a URL other than / and to an HTTP scheme that is
    different than what is used locally.

    In nginx:
    location /myprefix {
        proxy_pass http://192.168.0.1:5001;
        proxy_set_header Host $host;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Scheme $scheme;
        proxy_set_header X-Script-Name /myprefix;
        }

    :param app: the WSGI application
    """

    def __init__(self, app):
        self.app = app

    def __call__(self, environ, start_response):
        script_name = environ.get('HTTP_X_SCRIPT_NAME', '')
        if script_name:
            environ['SCRIPT_NAME'] = script_name

            path_info = environ['PATH_INFO']
            if path_info.startswith(script_name):
                environ['PATH_INFO'] = path_info[len(script_name):]

        scheme = environ.get('HTTP_X_SCHEME', '')
        if scheme:
            environ['wsgi.url_scheme'] = scheme

        return self.app(environ, start_response)

app.wsgi_app = ReverseProxied(app.wsgi_app)
