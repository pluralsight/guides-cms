"""
Main entry point for interacting with remote service APIs
"""

import base64

from flask_oauthlib.client import OAuth
from flask import session

from . import app

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


def primary_github_email_of_logged_in():
    """Get primary email address of logged in user"""

    resp = github.get('user/emails')
    if resp.status != 200:
        return None

    for email_data in resp.data:
        if email_data['primary']:
            return email_data['email']

        return None


def read_article_from_github(article):
    """
    Get rendered markdown article text from github API

    :params article: Article model object
    :returns: (article_text, sha)
    """

    sha = None
    text = rendered_markdown_from_github(article)

    if text is None:
        return (text, sha)

    sha = article_sha_from_github(article)

    return (text, sha)


def raw_article_from_github(article):
    """
    Get raw text from github API

    :params article: Article model object
    :returns: article text
    """

    text= None

    resp = github.get('repos/%s' % (article.github_api_location))
    if resp.status == 200:
        text = base64.b64decode(resp.data['content'])

    return text


def rendered_markdown_from_github(article):
    """
    Get rendered markdown article text from github API

    :params article: Article model object
    :returns: HTML article text
    """

    headers = {'accept': 'application/vnd.github.html'}
    resp = github.get('repos/%s' % (article.github_api_location),
                      headers=headers)

    if resp.status == 200:
        return resp.data

    return None


def article_sha_from_github(article):
    """
    Get article SHA from github

    :params article: Article model object
    :returns: SHA
    """

    sha = None
    resp = github.get('repos/%s' % (article.github_api_location))

    if resp.status == 200:
        sha = resp.data['sha']

    return sha


def commit_article_to_github(article, message, content, name, email, sha=None):
    """
    Save given article object and content to github

    :params article: Article object to save
    :params message: Commit message to save article with
    :params content: Content of article
    :params name: Name of author who wrote article
    :params email: Email address of author
    :params sha: Optional SHA of article if it already exists on github

    :returns: HTTP status of API request
    """

    content = base64.b64encode(content)
    commit_info = {'message': message, 'content': content,
                   'author': {'name': name, 'email': email}}

    if sha:
        commit_info['sha'] = sha

    # The flask-oauthlib API expects the access token to be in a tuple or a
    # list.  Not exactly sure why since the underlying oauthlib library has a
    # separate kwargs for access_token.  See flask_oauthlib.client.make_client
    # for more information.
    token = (app.config['REPO_OWNER_ACCESS_TOKEN'], )
    url = 'repos/%s' % (article.github_api_location)

    resp = github.put(url, data=commit_info, format='json', token=token)

    return resp.status


@github.tokengetter
def get_github_oauth_token():
    return session.get('github_token')
