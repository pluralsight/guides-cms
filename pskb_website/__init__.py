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
else:
    app.config.from_object(os.environ['APP_SETTINGS'])
    app.secret_key = app.config['SECRET_KEY']


db = SQLAlchemy(app)

import pskb_website.views
