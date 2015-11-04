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
            app.secret_key = os.environ[var]

    if 'DEBUG' in os.environ:
        app.debug = True

        print 'Config values'
        for key, value in app.config.iteritems():
            print key, value

else:
    app.config.from_object(os.environ['APP_SETTINGS'])
    app.secret_key = app.config['SECRET_KEY']


db = SQLAlchemy(app)

from pskb_website.models import Repo
import pskb_website.views

# Try to setup our default repo if it's not already in there.  This is the repo
# information all articles will be created with.
try:
    repo = Repo.query.filter_by(name=app.config['REPO_NAME'],
                                owner=app.config['REPO_OWNER']).first()
except Exception as err:
    # Protect against trying to import before the database is setup, etc.
    print 'Exception querying repos:', err
    app.config['REPO_ID'] = None
else:
    if repo is None:
        repo = Repo(app.config['REPO_OWNER'], app.config['REPO_NAME'])
        db.session.add(repo)
        db.session.commit()

    app.config['REPO_ID'] = repo.id
