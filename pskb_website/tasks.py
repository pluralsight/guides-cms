"""
Configure and define tasks for use with Celery
"""

import codecs
import os
import shutil
import subprocess
import tempfile
import json

from celery import Celery

from . import app
from . import PUBLISHED, IN_REVIEW, DRAFT
from . import remote
from .models import file as file_mod
from .models.article import get_available_articles_from_api

RETRIES = 5

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
        success = file_mod.update_article_listing(*args, **kwargs)
        if not success:
            app.logger.error(u'Failed updating article listing, args: "%s", kwargs: "%s"',
                             args, kwargs)


@celery.task()
def remove_from_listing(*args, **kwargs):
    """
    Remove a an article from file listing

    See .models.file.remove_from_listing for argument description.

    This wrapper just exists on top of .models.file.remove_from_listing so
    that it can be a normal function outside of celery tasks.
    """

    with app.test_request_context():
        success = file_mod.remove_article_from_listing(*args, **kwargs)
        if not success:
            app.logger.error(u'Failed removing article from listing, args: "%s", kwargs: "%s"',
                             args, kwargs)


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
        success = file_mod.sync_file_listing(articles, status, committer_name,
                                             committer_email)
        if not success:
            app.logger.error(u'Failed syncing article listing, status: "%s", committer_name: "%s", committer_email: "%s"',
                             status, committer_name, committer_email)


def change_publish_metadata(path, new_status):
    """
    Change publish_status in JSON metadata file
    """

    with codecs.open(path, 'r', encoding='utf-8') as file_obj:
        metadata = json.loads(file_obj.read(), encoding='utf-8')

    metadata['_publish_status'] = new_status

    # This was renamed so handle 'upgrading' when we see this old ref.
    try:
        del metadata['publish_status']
    except KeyError:
        pass

    with codecs.open(path, 'w', encoding='utf-8') as file_obj:
        file_obj.write(json.dumps(metadata, sort_keys=True, indent=4,
                                  separators=(',', ': ')))


@celery.task()
def move_article(curr_path, new_path, title, committer_name, committer_email,
                 new_publish_status=None):
    """
    Move article from one publish status to another

    :param curr_path: Current path to article w/o repo owner and name (eg.
                      in-review/python/title)
    :param new_path: Current path to article w/o repo owner and name (eg.
                     published/python/title)
    :param title: Title of article being moved
    :param committer_name: Name of user making change
    :param committer_email: Email of user making change
    :param new_publish_status: Optional new publish status if the article
                               should be moved and publish status changed
                               argument should be PUBLISHED, IN_REVIEW, or
                               DRAFT
    """

    app.logger.info(u'Moving %s from %s to %s', title, curr_path, new_path)

    url = remote.default_repo_path()
    clone_dir = tempfile.mkdtemp()

    user = app.config['REPO_OWNER']
    pwd = app.config['REPO_OWNER_ACCESS_TOKEN']

    url = u'https://%s:%s@github.com/%s.git' % (user, pwd, url)

    cmd = u'git clone %s %s' % (url, clone_dir)
    subprocess.check_call(cmd.split())

    cwd = os.getcwd()
    os.chdir(clone_dir)

    cmd = u'git config user.name %s' % (committer_name)
    subprocess.check_call(cmd.split())

    cmd = u'git config user.email %s' % (committer_email)
    subprocess.check_call(cmd.split())

    try:
        dirname = os.path.dirname(new_path)
        try:
            os.makedirs(dirname)
        except OSError:
            if not os.path.isdir(dirname):
                raise

        mv_cmd = u'git mv %s %s' % (curr_path, new_path)
        subprocess.check_call(mv_cmd.split(), cwd=clone_dir)

        if new_publish_status in (PUBLISHED, IN_REVIEW, DRAFT):
            md_file = os.path.join(clone_dir, new_path, u'details.json')
            change_publish_metadata(md_file, new_publish_status)

            cmd = u'git add %s' % (md_file)
            subprocess.check_call(cmd.split(), cwd=clone_dir)

        move_msg = u'"Moving \'%s\' from %s to %s"' % (title, curr_path,
                                                       new_path)
        cmd = [u'git', u'commit', u'-m', move_msg]

        subprocess.check_call(cmd, cwd=clone_dir)

        # Race condition here where we need to make sure to do a pull before a
        # push and the app itself could sneak commits in between.
        for cnt in xrange(RETRIES):
            try:
                subprocess.check_call(u'git push origin master'.split(), cwd=clone_dir)
                break
            except subprocess.CalledProcessError:
                if cnt >= RETRIES:
                    raise

                # Must do this in 2 steps b/c heroku git version doesn't have
                # the --commit option in git pull.
                subprocess.check_call(u'git fetch'.split(), cwd=clone_dir)
                cmd = [u'git', u'merge', u'origin/master',
                       u'-m', u'"Merged %s' % (move_msg),
                       u'--no-edit']
                subprocess.check_call(cmd, cwd=clone_dir)
    finally:
        os.chdir(cwd)
        shutil.rmtree(clone_dir)
