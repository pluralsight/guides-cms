"""
Main views of PSKB app
"""

from flask import redirect, url_for, session, request, render_template, flash, json, g

from . import app, db
from . import remote
from .models import Article, User, Tag


@app.route('/')
def index():
    # FIXME: This should only fetch the most recent x number.
    articles = remote.list_articles_from_github()

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

    # FIXME: Error handling
    me = remote.github.get('user').data
    email = remote.primary_github_email_of_logged_in()

    if email is None:
        flash('No primary email address found')

    user = User.query.filter_by(github_username=me['login']).first()
    if user is None:
        user = User(me['login'], email)
        db.session.add(user)
        db.session.commit()
    elif user.email != email:
        user.email = email
        db.session.add(user)
        db.session.commit()

    if me['name']:
        session['name'] = me['name']

    if me['login']:
        session['login'] = me['login']

        if 'name' not in session:
            session['name'] = me['login']

    g.profile_active = True
    return render_template('profile.html', body=me)


@app.route('/write/<path:article_path>/<sha>', methods=['GET'])
@app.route('/write/', defaults={'article_path': None, 'sha': None})
def write(article_path, sha):
    id_ = ''
    title = ''
    text = ''

    # FIXME: Require user to be logged in to see this view

    if article_path is not None:
        text, curr_sha, link = remote.article_details_from_github(article_path)

    if sha is None:
        sha = ''

    return render_template('editor.html', article_text=text, title=title,
                           path=article_path, sha=sha)


@app.route('/review/<path:article_path>', methods=['GET'])
def review(article_path):
    text, sha, github_url = remote.read_article_from_github(article_path)

    # We can still show the article without the url, but we need the text.
    if None in (text, sha, github_url):
        flash('Failing reading article from github')
        return redirect(url_for('index'))

    return render_template('article.html', text=text,
                           github_link=github_url,
                           path=article_path, sha=sha)


@app.route('/save/', methods=['POST'])
def save():
    user = User.query.filter_by(github_username=session['login']).first_or_404()

    # Data is stored in form with input named content which holds json. The
    # json has the 'real' data in the 'content' key.
    content = json.loads(request.form['content'])['content']

    path = request.form['path']

    if path:
        message = 'Updates to %s' % (request.form['title'])
    else:
        message = 'New article %s' % (request.form['title'])

    sha = request.form['sha']

    status = remote.commit_article_to_github(path, message, content,
                                             user.github_username, user.email,
                                             sha)

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

    if new_article:
        # FIXME: Handle errors
        db.session.delete(article)
        db.session.commit()

    flash('Failed creating article on github: %d' % (status))
    return redirect(url_for('index'))
