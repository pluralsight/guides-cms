"""
Main views of PSKB app
"""

from flask import redirect, url_for, session, request, render_template, flash
from flask_oauthlib.client import OAuth

from . import app
from .models import Article

oauth = OAuth(app)

github = oauth.remote_app(
    'github',
    consumer_key=app.config['GITHUB_CLIENT_ID'],
    consumer_secret=app.config['GITHUB_SECRET'],
    request_token_params={'scope': ['gist', 'user:email']},
    base_url='https://api.github.com/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://github.com/login/oauth/access_token',
    authorize_url='https://github.com/login/oauth/authorize'
)


@app.route('/')
def index():
    if 'github_token' in session:
        return redirect(url_for('user_profile'))

    return render_template('index.html')


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

    me = github.get('user').data

    session['logged_in'] = True
    if me['name']:
        session['name'] = me['name']

    if me['login']:
        session['login'] = me['login']

    return render_template('profile.html', body=me)


@app.route('/write/<github_id>')
@app.route('/write/', defaults={'github_id': None})
def write(github_id):
    # Grab the content from github
    if github_id is not None:
        pass
    else:
        github_id = ''

    # The path here tells the Epic Editor what the name of the local storage
    # file is called.  The file is overwritten if it exists so doesn't really
    # matter what name we use here.
    return render_template('editor.html', path='myfile', github_id=github_id)


@app.route('/save/', methods=['POST'])
def save():
    # Update content on github
    if not request.form['github_id']:
        pass
    # Create content on github
    else:
        pass

    # FIXME: We should create this gist as pluralsight not as this user but
    # with this user as the author.

    gist_info = {'files':  {'article.md': {'content': request.form['content']}}} 

    resp = github.post('gists', data=gist_info, format='json')

    if resp.status == 201:
        try:
            gist_url = 'https://gist.github.com/%s/%s' % (session['login'],
                                                          resp.data['id'])
        except KeyError:
            gist_url = ''

        return render_template('article.html', gist_url=gist_url)
    else:
        # FIXME: Handle errors
        flash('Failed creating gist: %d' % (resp.status))
        return redirect(url_for('index'))


@github.tokengetter
def get_github_oauth_token():
    return session.get('github_token')
