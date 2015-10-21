import os

from flask import Flask
from flask.ext.sqlalchemy import SQLAlchemy

app = Flask(__name__)

# Running on heroku
if 'HEROKU' in os.environ:
    from example_config import HEROKU_ENV_REQUIREMENTS

    # example_config.py provides a blueprint for which variables to look for in
    # the environment and set in our app config.
    for var in HEROKU_ENV_REQUIREMENTS:
        app.config.setdefault(var, os.environ[var])

        if var == 'SECRET_KEY':
            app.config.secret_key = os.environ[var]

    if 'DEBUG' in os.environ:
        app.debug = True

        print 'Config values'
        for key, value in app.config.iteritems():
            print key, value

else:
    app.config.from_object(os.environ['APP_SETTINGS'])
    app.secret_key = app.config['SECRET_KEY']


db = SQLAlchemy(app)

import pskb_website.views
