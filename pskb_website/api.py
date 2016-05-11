"""
Collection of URLs returning JSON responses
"""

import os
import re

import requests

from flask import Response, url_for, request, flash, json, g

from . import SLACK_URL
from . import app
from . import models
from . import tasks
from . import filters
from . import remote
from .lib import login_required


@app.route('/api/save/', methods=['POST'])
@login_required
def api_save():
    """
    Api: POST /api/save
    {path:'', title: '', sha:'', original_stack: '', content: '', stacks: []}
    """

    # Used to show link to slack for authors to get feedback
    g.slack_url = SLACK_URL

    user = models.find_user()
    if user is None:
        redirect_to = url_for('index')
        data = {'error': 'Cannot save unless logged in', 'redirect': redirect_to}
        return Response(response=json.dumps(data), status=401, mimetype='application/json')

    if user.email is None:
        flash('Unable to read email address from Github API to properly attribute your commit to your account. Please make sure you have authorized the application to access your email.', category='warning')
        # FIXME: stop using flash

    content = request.form['content']

    path = request.form['path']
    title = request.form['title']
    sha = request.form['sha']
    orig_stack = request.form['original_stack']
    first_commit = request.form['first_commit']

    if not content.strip() or not title.strip():
        data = {'error': 'Must enter title and body of guide'}
        return Response(response=json.dumps(data), status=400, mimetype='application/json')

    # Form only accepts 1 stack right now but we can handle multiple on the
    # back-end.
    if not request.form['stacks']:
        stacks = None
    else:
        stacks = request.form.getlist('stacks')

        # FIXME: This is not the best solution. We're making this task
        # synchronous but it's just a few git commands so hoping it will be
        # quick. Also it only happens in the rare case where a stack is
        # changed.  We need to wait for the file move so we can maintain the
        # history of the article through the move.
        if path and orig_stack and stacks[0] != orig_stack:
            new_path = models.change_article_stack(path, orig_stack, stacks[0],
                                                   title, user.login,
                                                   user.email)

            if new_path is None:
                flash('Failed changing guide stack', category='error')
                # FIXME? return an error?
            else:
                path = new_path

    new_article = False
    if path:
        message = 'Updates to "%s"' % (title)
    else:
        new_article = True
        message = 'New guide, "%s"' % (title)

        # Go ahead and make sure we don't have an article with the same stack
        # and title.  This would lead to duplicate URLs and we want to
        # prevent users from ever creating a clash instead of detecting this
        # change
        article = models.search_for_article(title, stacks=stacks)
        if article is not None:
            if stacks is None:
                msg = u'Please try choosing a stack. The title "%s" is already used by a guide.' % (title)
            else:
                msg = u'Please try choosing a different stack/title combination. The title "%s" is already used by a guide with the stack "%s".' % (title, ','.join(stacks))
            data = {'error': msg}
            return Response(response=json.dumps(data), status=422, mimetype='application/json')

    # Hidden option for admin to save articles to our other repo that's not
    # editable
    # TODO: move this to another endpoint
    repo_path = None
    if request.form.get('secondary_repo', None) is not None:
        repo_path = '%s/%s' % (app.config['SECONDARY_REPO_OWNER'],
                               app.config['SECONDARY_REPO_NAME'])

    article = models.branch_or_save_article(title, path, message, content,
                                            user.login, user.email, sha,
                                            user.avatar_url,
                                            stacks=stacks,
                                            repo_path=repo_path,
                                            author_real_name=user.name,
                                            first_commit=first_commit)

    if not article:
        # Was this a new guide or update?
        if path:
            redirect_to = request.referrer or url_for('index')
        else:
            redirect_to = url_for('write')

        data = {'error': 'Failed creating guide on github. Please try again.',
                'redirect': redirect_to}

        return Response(response=json.dumps(data), status=500, mimetype='application/json')

    # TODO: move this to another endpoint
    if repo_path is not None:
        redirect_to = url_for('partner', article_path=article.path, branch=article.branch)
        data = {'msg': 'Saved into admin repository', 'redirect': redirect_to}
        if new_article:
            return Response(response=json.dumps(data), status=201, mimetype='application/json')
        else:
            return Response(response=json.dumps(data), status=200, mimetype='application/json')

    # We only have to worry about this on the master branch because we never
    # actually use file listings on other branches.
    if article.branch == u'master':
        # Use these filter wrappers so we get absolute URL instead of relative
        # URL to this specific site.
        url = filters.url_for_article(article)
        author_url = filters.url_for_user(article.author_name)

        tasks.update_listing.delay(url,
                                   article.title,
                                   author_url,
                                   article.author_real_name,
                                   user.login,
                                   user.email,
                                   author_img_url=article.image_url,
                                   thumbnail_url=article.thumbnail_url,
                                   stacks=article.stacks,
                                   branch=article.branch,
                                   status=article.publish_status)

    redirect_to = filters.url_for_article(article, branch=article.branch, saved=1)
    data = {'redirect': redirect_to}
    status = 200

    if new_article:
        status = 201

    return Response(response=json.dumps(data), status=status,
                    mimetype='application/json')


@app.route('/img_upload/', methods=['POST'])
@login_required
def img_upload():
    """Image upload POST page"""

    user = models.find_user()
    if user is None:
        app.logger.error('Cannot upload image unless logged in')
        return Response(response='', status=500, mimetype='application/json')

    file_ = request.files['file']

    try:
        ext = file_.filename.split(os.extsep)[1]
    except IndexError:
        ext = ''

    # Always save images to master branch because image uploads might happen
    # before the article is saved so don't know the article name or branch to
    # save alongside.
    url = models.save_image(file_.stream, ext, 'Saving new guide image',
                            user.login, user.email, branch=u'master')

    if url is None:
        app.logger.error('Failed uploading image')
        return Response(response='', status=500, mimetype='application/json')

    return Response(response=json.dumps(url), status=200,
                    mimetype='application/json')


@app.route('/api/slack_stats/', methods=['GET'])
def slack_stats():
    """
    Screen-scrape slack signup app since it's dynamic with node.js and grabs
    from slack API.
    """

    stats = ''
    resp = requests.get(SLACK_URL)

    if resp.status_code == 200:
        user_count = re.search(r'<p class="status">(.*?)</p>', resp.content)
        if user_count is not None:
            stats = user_count.group(1)

    return Response(response=json.dumps({'text': stats}), status=200,
                    mimetype='application/json')


@app.route('/gh_rate_limit')
def gh_rate_limit():
    """Debug request to view rate limit on Github"""

    return Response(response=json.dumps(remote.check_rate_limit()), status=200,
                    mimetype='application/json')


@app.route('/api/add-heart/', methods=['POST'])
@login_required
def add_heart():
    """
    Add heart to referenced article and return new heart count as JSON
    """

    user = models.find_user()
    if user is None:
        data = {'error': 'Cannot heart unless logged in'}
        return Response(response=json.dumps(data), status=401,
                        mimetype='application/json')

    count = models.add_heart(request.form['stack'], request.form['title'],
                             user.login)

    return Response(response=json.dumps({'count': count}), status=200,
                    mimetype='application/json')


@app.route('/api/remove-heart/', methods=['POST'])
@login_required
def remove_heart():
    """
    Remove heart to referenced article and return new heart count as JSON
    """

    user = models.find_user()
    if user is None:
        data = {'error': 'Cannot heart unless logged in'}
        return Response(response=json.dumps(data), status=401,
                        mimetype='application/json')

    count = models.remove_heart(request.form['stack'], request.form['title'],
                                user.login)

    return Response(response=json.dumps({'count': count}), status=200,
                    mimetype='application/json')
