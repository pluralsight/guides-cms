"""
Collection of URLs responding to Github webhooks API
"""

import json

from . import app
from . import cache
from .models.article import ARTICLE_FILENAME

from flask import request, Response


@app.route('/github_push', methods=['POST'])
def push_event():
    """
    Detect if any of the pushed commits dealt with a guide and invalidate the
    cache for those guides.
    """

    finished = Response(response='', status=200, mimetype='application/json')

    commits = _safe_index_json(request.json, 'commits',
                               'No commits found in push event')
    if commits is None:
        return finished

    ref = _safe_index_json(request.json, 'ref', 'No ref found in push event')
    if ref is None:
        return finished

    branch = ref.split('/')[-1]

    for commit in commits:
        mod_files = _safe_index_json(commit, 'modified',
                                     'No modified found in push event')
        if mod_files is None:
            continue

        for path in _articles(mod_files):
            app.logger.debug('Invalidating path: "%s", branch: "%s" from push event',
                             path, branch)
            cache.delete_file(path, branch)

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

    file_path = u'/%s' % (ARTICLE_FILENAME)

    for path in paths:
        if path.endswith(file_path):
            yield path.split(file_path)[0]
