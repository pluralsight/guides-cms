"""
File to easily switch between configurations between production and
development, etc.
"""

import os


# You must set each of these in your heroku environment with the heroku
# config:set command. See README.md for more information.
HEROKU_ENV_REQUIREMENTS = ('HEROKU', 'SECRET_KEY', 'GITHUB_CLIENT_ID',
                           'GITHUB_SECRET')


class Config(object):
    DEBUG = False
    CSRF_ENABLED = True
    GITHUB_CLIENT_ID = 'replace-me'
    GITHUB_SECRET = 'replace-me'
    HEROKU = False
    SECRET_KEY = 'not-a-good-value'

    # This should automatically be set by heroku if you've added a database to
    # your app.
    SQLALCHEMY_DATABASE_URI = os.environ['DATABASE_URL']


class DevelopmentConfig(Config):
    DEBUG = True
