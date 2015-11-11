"""
Main views of PSKB app
"""

from flask import redirect, url_for, session, request, render_template, flash, json, g

from . import app
from . import remote
from . import models


@app.route('/')
def index():
    # FIXME: This should only fetch the most recent x number.
    articles = models.get_available_articles()

    g.index_active = True
    return render_template('index.html', articles=articles)


@app.route('/login')
def login():
    return remote.github.authorize(callback=url_for('authorized', _external=True))


@app.route('/logout')
def logout():
    session.pop('github_token', None)
    return redirect(url_for('index'))


@app.route('/github/authorized')
def authorized():
    resp = remote.github.authorized_response()
    if resp is None:
        return 'Access denied: reason=%s error=%s' % (
            request.args['error'], request.args['error_description'])

    session['github_token'] = (resp['access_token'], '')

    return redirect(url_for('user_profile'))


@app.route('/user/')
def user_profile():
    if 'github_token' not in session:
        return redirect(url_for('login'))

    me = models.find_user()

    if me.name:
        session['name'] = me.name

    if me.login:
        session['login'] = me.login

        if 'name' not in session:
            session['name'] = me.login

    g.profile_active = True
    return render_template('profile.html', user=me)


@app.route('/write/<path:article_path>/<sha>', methods=['GET'])
@app.route('/write/', defaults={'article_path': None, 'sha': None})
def write(article_path, sha):
    # FIXME: Require user to be logged in to see this view

    article = None

    if article_path is not None:
        article = models.read_article(article_path, rendered_text=False)

        if article.sha is None:
            article.sha = ''

    return render_template('editor.html', article=article)


@app.route('/review/<path:article_path>', methods=['GET'])
def review(article_path):
    article = models.read_article(article_path)
    if article is None:
        flash('Failing reading article')
        return redirect(url_for('index'))

    return render_template('article.html', article=article)


@app.route('/save/', methods=['POST'])
def save():
    user = models.find_user(session['login'])
    if user is None:
        flash('Cannot save unless logged in')
        return render_template('index.html'), 404

    # Data is stored in form with input named content which holds json. The
    # json has the 'real' data in the 'content' key.
    content = json.loads(request.form['content'])['content']

    path = request.form['path']

    if path:
        message = 'Updates to %s' % (request.form['title'])
    else:
        message = 'New article %s' % (request.form['title'])

    sha = request.form['sha']

    status = models.save_article(path, message, content, user.login,
                                 user.email, sha)

    # FIXME: If there's an article_id:
    #   - Grab it
    #   - Check if this author is the owner
    #       - If yes, just submit a put request to github to change the
    #         contents of the file
    #       - if no, submit a put request to github to create the contents

    # FIXME: Need to handle forks here somehow too, but maybe that's taken care
    # of by the fork action.

    # FIXME: Need to detect if this save is for a forked article or not.
    #   if it's for a forked article we should call github with a pull request
    #   after this is done.

    # Successful creation
    if status in (200, 201):
        return redirect(url_for('review', article_path=path))

    flash('Failed creating article on github: %d' % (status))
    return redirect(url_for('index'))
