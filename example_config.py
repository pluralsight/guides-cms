"""
File to easily switch between configurations between production and
development, etc.
"""

import os


# You must set each of these in your heroku environment with the heroku
# config:set command. See README.md for more information.
HEROKU_ENV_REQUIREMENTS = ('HEROKU', 'SECRET_KEY', 'GITHUB_CLIENT_ID',
                           'GITHUB_SECRET', 'REPO_OWNER', 'REPO_NAME',
                           'REPO_OWNER_ACCESS_TOKEN', 'REDISCLOUD_URL',
                           'REDIS_HEARTS_DB_URL', 'REDIS_URL',
                           'MAILCHIMP_API_KEY', 'MAILCHIMP_LIST_ID',
                           'MAILCHIMP_STACKS_GROUP_NAME',
                           'SECONDARY_REPO_OWNER', 'SECONDARY_REPO_NAME',
                           'DOMAIN', 'CELERY_BROKER_URL',
                           'CELERY_TASK_SERIALIZER', 'HOSTING_SUBDIRECTORY',
                           'IGNORE_STATS_FOR', 'WEBHOOK_SECRET',
                           'ENABLE_HEARTING')


class Config(object):
    DEBUG = False
    CSRF_ENABLED = True
    HEROKU = False
    SECRET_KEY = 'not-a-good-value'

    # Details of the repo where all articles are stored.  The GITHUB_CLIENT_ID
    # and GITHUB_SECRET should allow full-access to this database.
    GITHUB_CLIENT_ID = 'replace-me'
    GITHUB_SECRET = 'replace-me'
    REPO_OWNER = None
    REPO_NAME = None
    REPO_OWNER_ACCESS_TOKEN = None

    CELERY_TASK_SERIALIZER = 'json'
    CELERY_BROKER_URL = None

    # Secondary (optional) repo for articles that are not editable
    SECONDARY_REPO_OWNER = None
    SECONDARY_REPO_NAME = None

    # For caching
    REDISCLOUD_URL = None

    # For persistent hearts on guides (optional)  We'll fallback to
    # REDISCLOUD_URL if this does not exist. Finally if REDISCLOUD_URL does not
    # exist hearting won't be saved, but the application will still function.
    REDIS_HEARTS_DB_URL = None
    ENABLE_HEARTING = False

    # For celery
    REDIS_URL = None

    MAILCHIMP_API_KEY = None
    MAILCHIMP_LIST_ID = None
    MAILCHIMP_STACKS_GROUP_NAME = None

    DOMAIN = ''

    # Only needed if using github webhooks
    WEBHOOK_SECRET = ''

    # Set this to something like '/guides' if your hosting this application on
    # a subdirectory with a proxy pass rule that sends all /guides/* requests
    # to this app.  Thus, this app responds to '/guides' with the '/' rule.
    HOSTING_SUBDIRECTORY = ''

    # CSV string of user login names to ignore stats for.  This is useful if
    # you want to ignore the repo owner. You can easily add to this list.
    IGNORE_STATS_FOR = ''
    if REPO_OWNER is not None:
        IGNORE_STATS_FOR = ','.join([REPO_OWNER])


class DevelopmentConfig(Config):
    DEBUG = True
