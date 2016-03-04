"""
Configure and define tasks for use with Celery
"""

from celery import Celery

from . import app
from .models import file as file_mod
from .models.article import get_available_articles_from_api


def make_celery(app):
    celery = Celery(app.import_name, broker=app.config['CELERY_BROKER_URL'])
    celery.conf.update(app.config)
    TaskBase = celery.Task

    class ContextTask(TaskBase):
        abstract = True
        def __call__(self, *args, **kwargs):
            with app.app_context():
                return TaskBase.__call__(self, *args, **kwargs)

    celery.Task = ContextTask
    return celery


celery = make_celery(app)


# Updating the file listing files is done via celery because we need a queue to
# synchonize all the changes and avoid conflicts.  These files are updated by
# all users when they create/remove/publish/unpublish articles so we have to be
# sure that queue this up so things happen in the correct order.  The queue
# reduces the risk of reading the SHA of the file listing and it changing
# before we can updated it.  So, the queue should be the only thing that
# changes these files.

# We still run the risk of these files being updated locally and pushed to
# github between the time we've read the SHA from the API and changed the file.
# Not a great way to reduce this risk with the current design...

@celery.task()
def update_listing(*args, **kwargs):
    """
    Update file listing with data as described by arguments

    See .models.file.update_article_listing for argument description

    This wrapper just exists on top of .models.file.update_article_listing so
    that it can be a normal function outside of celery tasks.
    """

    with app.test_request_context():
        file_mod.update_article_listing(*args, **kwargs)


@celery.task()
def remove_from_listing(*args, **kwargs):
    """
    Remove a an article from file listing

    See .models.file.remove_from_listing for argument description.

    This wrapper just exists on top of .models.file.remove_from_listing so
    that it can be a normal function outside of celery tasks.
    """

    with app.test_request_context():
        file_mod.remove_article_from_listing(*args, **kwargs)


@celery.task()
def synchronize_listing(status, committer_name, committer_email):
    """
    Synchronize file listing with the articles that exist via the API

    :param status: PUBLISHED, IN_REVIEW, or DRAFT
    :param committer_name: Name of user making change
    :param committer_email: Email of user making change

    Note this is an expensive operation because it does a full scan of all the
    articles in the repo so it can use up quite a few API requests and time.
    """

    with app.test_request_context():
        articles = get_available_articles_from_api(status)
        file_mod.sync_file_listing(articles, status, committer_name,
                                   committer_email)
