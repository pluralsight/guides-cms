"""
Configure Flask app instance
"""

import logging
import os

from flask import Flask

app = Flask(__name__)

# Running on heroku
if 'HEROKU' in os.environ:
    import example_config

    # example_config.py provides a blueprint for which variables to look for in
    # the environment and set in our app config.
    for var in example_config.HEROKU_ENV_REQUIREMENTS:
        app.config.setdefault(var, os.environ[var])

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
    app.logger.addHandler(logging.StreamHandler())


import pskb_website.views
import pskb_website.filters

app.jinja_env.filters['date_string'] = filters.date_string
app.jinja_env.filters['url_for_article'] = filters.url_for_article
app.jinja_env.filters['url_for_user'] = filters.url_for_user
app.jinja_env.filters['author_name'] = filters.author_name
