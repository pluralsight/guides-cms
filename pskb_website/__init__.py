import os

from flask import Flask

import example_config

app = Flask(__name__)

# Running on heroku
if 'HEROKU' in os.environ:
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
        print 'Unable to find configuration, using example'
        app.config.from_object(example_config.DevelopmentConfig)

    app.secret_key = app.config['SECRET_KEY']


import pskb_website.views
