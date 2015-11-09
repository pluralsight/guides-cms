"""
Main entry point for interacting with remote service APIs
"""

import base64
import collections

from flask_oauthlib.client import OAuth
from flask import session

from . import app
from . import models

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


article = collections.namedtuple('article', 'title, path')


def list_articles_from_github(limit=None):
    """
    Get list of article links from github

    :params limit: Optional limit of the number of articles to return
    :returns: List of article tuples containing title and path
    """

    articles = []
    repo = models.main_article_path()

    sha = repo_sha_from_github(repo)
    if sha is None:
        return articles

    resp = github.get('repos/%s/git/trees/%s?recursive=1' % (repo, sha))
    if resp.status != 200:
        return articles

    # FIXME: Handle this scenario
    assert not resp.data['truncated'], 'Too many articles for API call'

    for obj in resp.data['tree']:
        if obj['path'].endswith('article.md'):
            tokens = obj['path'].split('/')

            # FIXME: This is where we will read the meta data file associated
            # and pull out title.
            title = tokens[0]

            articles.append(article(title, '%s/%s' % (repo, obj['path'])))
            if limit is not None and len(articles) == limit:
                return articles

    return articles


def repo_sha_from_github(repo, branch='master'):
    """
    Get sha from head of given repo

    :params repo: Path to repo (owner/repo_name)
    :params branch: Name of branch to get sha for
    :returns: Sha of branch
    """

    resp = github.get('repos/%s/git/refs/heads/%s' % (repo, branch))
    if resp.status != 200:
        return None

    return resp.data['object']['sha']


def primary_github_email_of_logged_in():
    """Get primary email address of logged in user"""

    resp = github.get('user/emails')
    if resp.status != 200:
        return None

    for email_data in resp.data:
        if email_data['primary']:
            return email_data['email']

        return None


def read_article_from_github(path):
    """
    Get rendered markdown article text from github API, sha, and github link

    :params path: Path to article (<owner>/<repo>/<dir>/.../article.md>)
    :returns: (article_text, sha)
    """

    sha = None
    link = None
    text = rendered_markdown_from_github(path)

    if text is None:
        return (text, sha, link)

    sha, link = article_details_from_github(path)

    return (text, sha, link)


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


def rendered_markdown_from_github(path):
    """
    Get rendered markdown article text from github API

    :params path: Path to article (<owner>/<repo>/<dir>/.../article.md>)
    :returns: HTML article text
    """

    owner, repo, article_path = split_full_article_path(path)

    headers = {'accept': 'application/vnd.github.html'}
    resp = github.get('repos/%s/%s/contents/%s' % (owner, repo, article_path),
                      headers=headers)

    if resp.status == 200:
        return resp.data

    return None


def article_details_from_github(path):
    """
    Get article SHA and github url from github

    :params path: Path to article (<owner>/<repo>/<dir>/.../article.md>)
    :returns: (SHA, github_url)
    """

    sha = None
    link = None
    owner, repo, article_path = split_full_article_path(path)

    resp = github.get('repos/%s/%s/contents/%s' % (owner, repo, article_path))

    if resp.status == 200:
        sha = resp.data['sha']
        link = resp.data['_links']['html']

    return (sha, link)


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


def split_full_article_path(path):
    """
    Split full article path into owner, repo, and article_path

    :params path: Path to article (<owner>/<repo>/<dir>/.../article.md>)
    :returns: (owner, repo, article_path)
    """

    tokens = path.split('/')

    owner = tokens[0]
    repo = tokens[1]
    article_path = '/'.join(tokens[2:])

    return (owner, repo, article_path)
