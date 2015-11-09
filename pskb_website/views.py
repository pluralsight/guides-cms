"""
Main views of PSKB app
"""

from flask import redirect, url_for, session, request, render_template, flash, json

from . import app, db
from . import remote
from .models import Article, User, Tag


@app.route('/')
def index():
    # FIXME: This should only fetch the most recent x number.
    articles = remote.list_articles_from_github()

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
    print 'token = ', session['github_token']

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

    return render_template('profile.html', body=me)


@app.route('/write/<path:article_path>/<sha>', methods=['GET'])
@app.route('/write/', defaults={'article_path': None, 'sha': None})
def write(article_path, sha):
    id_ = ''
    title = ''
    text = ''

    # FIXME: Require user to be logged in to see this view

    if article_path is not None:
        article = Article.query.filter_by(path=article_path).first_or_404()
        id_ = article.id
        title = article.title
        text = remote.raw_article_from_github(article)

    if sha is None:
        sha = ''

    return render_template('editor.html', article_text=text, title=title,
                           article_id=id_, sha=sha)


@app.route('/fork/<path>')
def fork():
    # FIXME:
    #   - Create new article object
    #   - Get logged in users information
    #   - Submit a fork API request
    #   - Save the article's repo as the forked address

    # FIXME: We don't need to know who forked what b/c github tracks that for
    # us

    # FIXME: Require user to be logged in to see this view
    pass


@app.route('/review/<path:article_path>', methods=['GET'])
def review(article_path):
    article = Article.query.filter_by(path=article_path).first_or_404()
    text, sha = remote.read_article_from_github(article)

    # We can still show the article without the url, but we need the text.
    if text is None or sha is None:
        flash('Failing reading article from github')
        return redirect(url_for('index'))

    return render_template('article.html', text=text,
                           github_link=article.github_url,
                           path=article.path, sha=sha)


@app.route('/save/', methods=['POST'])
def save():
    user = User.query.filter_by(github_username=session['login']).first_or_404()

    new_article = False

    try:
        article_id = int(request.form['article_id'])
    except ValueError:
        article = Article(title=request.form['title'], author_id=user.id,
                          repo_id=app.config['REPO_ID'])
        new_article = True
    else:
        article = Article.query.get(article_id)

        # FIXME: Cannot change title now because that would change the path
        article.title = request.form['title']

    # Save article locally first so we can have all the relationships to get
    # the location to store on github.
    db.session.add(article)
    db.session.commit()
    article.update_path()
    db.session.add(article)
    db.session.commit()

    # Data is stored in form with input named content which holds json. The
    # json has the 'real' data in the 'content' key.
    content = json.loads(request.form['content'])['content']

    if new_article:
        message = 'New article %s' % (article.title)
    else:
        message = 'Updates to %s' % (article.title)

    sha = request.form['sha']

    status = remote.commit_article_to_github(article, message, content,
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
        return redirect(url_for('review', article_path=article.path))

    if new_article:
        # FIXME: Handle errors
        db.session.delete(article)
        db.session.commit()

    flash('Failed creating article on github: %d' % (status))
    return redirect(url_for('index'))
