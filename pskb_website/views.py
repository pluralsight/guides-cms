"""
Main views of PSKB app
"""

import base64

from flask import redirect, url_for, session, request, render_template, flash, json
from flask_oauthlib.client import OAuth

from . import app, db
from .models import Article, User, Tag

oauth = OAuth(app)

github = oauth.remote_app(
    'github',
    consumer_key=app.config['GITHUB_CLIENT_ID'],
    consumer_secret=app.config['GITHUB_SECRET'],
    request_token_params={'scope': ['public_repo', 'user:email']},
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize'
)


@app.route('/')
def index():
    # FIXME: This should only fetch the most recent x number.
    articles = Article.query.all()

    return render_template('index.html', articles=articles)


@app.route('/login')
def login():
    return github.authorize(callback=url_for('authorized', _external=True))


@app.route('/logout')
def logout():
    session.pop('github_token', None)
    return redirect(url_for('index'))


@app.route('/github/authorized')
def authorized():
    resp = github.authorized_response()
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
    me = github.get('user').data
    email = get_primary_github_email_of_logged_in()

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


@app.route('/write/<path>')
@app.route('/write/', defaults={'path': None})
def write(path):
    id_ = ''
    title = ''
    text = ''

    if path is not None:
        article = Article.query.first_or_404(path=path)
        id_ = article.id
        title = article.title

        resp = github.get('repos/%s' % (article.github_api_location))

        if resp.status == 200:
            text = base64.b64decode(resp.data['content'])

    # The path here tells the Epic Editor what the name of the local storage
    # file is called.  The file is overwritten if it exists so doesn't really
    # matter what name we use here.
    return render_template('editor.html', path='myfile', article_text=text,
                           title=title, article_id=id_)


@app.route('/fork/<path>')
def fork():
    # FIXME:
    #   - Create new article object
    #   - Get logged in users information
    #   - Submit a fork API request
    #   - Save the article's repo as the forked address

    # FIXME: We don't need to know who forked what b/c github tracks that for
    # us
    pass


@app.route('/review/<path:article_path>', methods=['GET'])
def review(article_path):
    article = Article.query.filter_by(path=article_path).first_or_404()
    text = read_article_from_github(article)

    # We can still show the article without the url, but we need the text.
    if text is None:
        flash('Failing reading article from github')
        return redirect(url_for('index'))

    return render_template('article.html', text=text,
                           github_link=article.github_url)


@app.route('/save/', methods=['POST'])
def save():
    user = User.query.filter_by(github_username=session['login']).first_or_404()

    try:
        article_id = int(request.form['article_id'])
    except ValueError:
        article = Article(title=request.form['title'], author_id=user.id,
                          repo_id=app.config['REPO_ID'])
    else:
        article = Article.query.get(article_id)
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

    message = 'New article %s' % (article.title)
    status = commit_article_to_github(article, message, content,
                                      user.github_username, user.email)

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

    # FIXME: Handle errors
    db.session.delete(article)
    db.session.commit()
    flash('Failed creating article on github: %d' % (status))
    return redirect(url_for('index'))


def commit_article_to_github(article, message, content, name, email):
    """
    Save given article object and content to github

    :params article: Article object to save
    :params message: Commit message to save article with
    :params content: Content of article
    :params name: Name of author who wrote article
    :params email: Email address of author
    :returns: HTTP status of API request
    """

    content = base64.b64encode(content)
    commit_info = {'message': message, 'content': content,
                   'author': {'name': name, 'email': email}}


    # The flask-oauthlib API expects the access token to be in a tuple or a
    # list.  Not exactly sure why since the underlying oauthlib library has a
    # separate kwargs for access_token.  See flask_oauthlib.client.make_client
    # for more information.
    token = (app.config['REPO_OWNER_ACCESS_TOKEN'], )
    url = 'repos/%s' % (article.github_api_location)

    resp = github.put(url, data=commit_info, format='json', token=token)

    return resp.status


def read_article_from_github(article):
    """
    Get rendered markdown article text from github API

    :params article: Article model object
    :returns: article_text
    """

    url = 'repos/%s' % (article.github_api_location)
    headers = {'accept': 'application/vnd.github.html'}
    resp = github.get(url, headers=headers)

    if resp.status == 200:
        return resp.data

    # FIXME: Handle errors
    flash('Failed reading content from github: %d' % (resp.status))
    return None


def get_primary_github_email_of_logged_in():
    """Get primary email address of logged in user"""

    resp = github.get('user/emails')
    if resp.status != 200:
        flash('Failed reading user email addresses: %s' % (resp.status))
        return None

    for email_data in resp.data:
        if email_data['primary']:
            return email_data['email']

    flash('No primary email address found')
    return None


@github.tokengetter
def get_github_oauth_token():
    return session.get('github_token')
