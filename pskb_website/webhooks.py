"""
Collection of URLs responding to Github webhooks API
"""

import hmac
from hashlib import sha1
import json
import re
from sys import hexversion

from flask import request, Response, abort

from . import app
from . import DRAFT
from . import cache
from . import models
from .lib import read_article
from .utils import slugify_stack
from .models import article as article_mod
from .forms import STACK_OPTIONS

STACKS_OR = '|'.join(re.escape(slugify_stack(unicode(s))) for s in STACK_OPTIONS + (article_mod.DEFAULT_STACK,))


def validate_webhook_source():
    """
    Validate that a webhook request came from github.com using our customized
    secret code

    This function was inspired by:
        - https://github.com/carlos-jenkins/python-github-webhooks/blob/master/webhooks.py
    """

    secret = app.config.get('WEBHOOK_SECRET')
    if not secret:
        return

    # Only SHA1 is supported
    header_signature = request.headers.get('X-Hub-Signature')
    if header_signature is None:
        app.logger.warning('No X-Hub-Signature header in webhook request')
        abort(403)

    sha_name, signature = header_signature.split('=')
    if sha_name != 'sha1':
        app.logger.warning('Incorrect header signature in webhook request: "%s"',
                           header_signature)
        abort(501)

    # HMAC requires the key to be bytes, but data is string
    mac = hmac.new(str(secret), msg=request.data, digestmod=sha1)
    correct_signature = str(mac.hexdigest())

    # Python prior to 2.7.7 does not have hmac.compare_digest
    if hexversion >= 0x020707F0:
        if not hmac.compare_digest(correct_signature, str(signature)):
            app.logger.warning('Webhook request did not come from github, is: "%s", shb: "%s"',
                               signature, correct_signature)
            abort(403)
    else:
        # What compare_digest provides is protection against timing
        # attacks; we can live without this protection for a web-based
        # application
        if correct_signature != str(signature):
            app.logger.warning('Webhook request did not come from github, is: "%s", shb: "%s"',
                               signature, correct_signature)
            abort(403)


@app.route('/github_push', methods=['POST'])
def push_event():
    """
    Detect if any of the pushed commits dealt with a guide and invalidate the
    cache for those guides.
    """

    validate_webhook_source()

    finished = Response(response='', status=200, mimetype='application/json')

    commits = _safe_index_json(request.json, 'commits',
                               'No commits found in push event')
    if commits is None:
        return finished

    ref = _safe_index_json(request.json, 'ref', 'No ref found in push event')
    if ref is None:
        return finished

    branch = ref.split('/')[-1]
    cleared = set()

    for commit in commits:
        mod_files = _safe_index_json(commit, 'modified',
                                     'No modified found in push event')
        if mod_files is None:
            continue

        for path in _articles(mod_files):
            if (path, branch) in cleared:
                continue

            app.logger.debug('Invalidating path: "%s", branch: "%s" from push event',
                             path, branch)

            cache.delete_file(path, branch)
            cleared.add((path, branch))

    return finished


@app.route('/github_delete', methods=['POST'])
def delete_event():
    """
    Detect if a branch was deleted and we need to update the list of branches
    on any guides
    """

    validate_webhook_source()

    finished = Response(response='', status=200, mimetype='application/json')

    ref = _safe_index_json(request.json, 'ref', 'No ref found in delete event')
    if ref is None:
        return finished

    ref_type = _safe_index_json(request.json, 'ref_type',
                                'No ref_type found in delete event')

    if ref_type is None or ref_type != 'branch' or ref_type == 'master':
        return finished

    branch = ref.split('/')[-1]

    # There are '-' separating the components.
    match = re.match(r'([a-zA-Z_-]+?)-(%s{1})-(.+)' % (STACKS_OR), ref)
    if match is None:
        app.logger.warning('Failed parsing ref from delete event, ref: %s', ref)
        return finished

    if len(match.groups()) != 3:
        app.logger.warning('Unable to match all 3 compenents from delete event, ref: %s', ref)
        return finished

    username, stack, title = match.groups()

    # Find article, arbitrarily starting at DRAFT status.
    # NOTE we use the master branch here b/c that's where all the articles'
    # branches are stored/deleted from.

    article = read_article(stack, title, u'master', DRAFT, rendered_text=False)
    if article is None:
        app.logger.warning('No article found for delete event, stack: "%s", title: "%s", branch: "%s"',
                           stack, title, branch)
        return finished

    if not article_mod.delete_branch(article, branch):
        app.logger.warning('Failed deleting branch for delete event, stack: "%s", title: "%s", branch: "%s"',
                           stack, title, branch)
        return finished

    app.logger.debug('Deleted branch for delete event, stack: "%s", title: "%s", branch: "%s"',
                     stack, title, branch)

    return finished


def _safe_index_json(json_, key, warning_message):
    """
    Safely index the given JSON object

    :param json_: JSON object
    :param key: Key to inspect in JSON object
    :param warning_message: Warning message to log if key is missing
    :returns: None if not found or value at key
    """

    try:
        return json_[key]
    except KeyError:
        app.logger.warning('%s, json:%s', warning_message,
                           json.dumps(request.json))
        return None


def _articles(paths):
    """
    Generator through list of articles from a list of paths

    :param paths: List of file paths
    """

    file_path = u'/%s' % (article_mod.ARTICLE_FILENAME)

    for path in paths:
        if path.endswith(file_path) or path in models.MARKDOWN_FILES:
            yield path.split(file_path)[0]
