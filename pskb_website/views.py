"""
Main views of PSKB app
"""

import os

from flask import redirect, url_for, session, request, jsonify
from flask_oauthlib.client import OAuth

from . import app
from .models import Article

oauth = OAuth(app)

github = oauth.remote_app(
    'github',
    consumer_key=app.config['GITHUB_CLIENT_ID'],
    consumer_secret=app.config['GITHUB_SECRET'],
    request_token_params={'scope': 'user:email'},
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

    return 'How about you <a href="/login">Login?</a>'


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
    if 'github_token' in session:
        me = github.get('user')
        return jsonify(me.data)

    return redirect(url_for('login'))


@github.tokengetter
def get_github_oauth_token():
    return session.get('github_token')
