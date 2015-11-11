"""
Main entry point for interacting with remote service APIs
"""

import base64
import collections

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


article_details = collections.namedtuple('article_details', 'path, sha')


def articles_from_github(repo, article_filename, limit=None):
    """
    Iterate through articles from github

    :params repo: Path to repo to read articles from
    :params article_filename: Name of filename that's considered an article
    :params limit: Optional limit of the number of articles to return

    :returns: Iterator through article tuples containing sha and path
    """

    sha = repo_sha_from_github(repo)
    if sha is None:
        raise StopIteration

    resp = github.get('repos/%s/git/trees/%s?recursive=1' % (repo, sha))
    token = (app.config['REPO_OWNER_ACCESS_TOKEN'], )

    if resp.status != 200:
        # FIXME: Raise exception
        raise StopIteration

    # FIXME: Handle this scenario
    assert not resp.data['truncated'], 'Too many articles for API call'

    count = 0
    for obj in resp.data['tree']:
        if obj['path'].endswith(article_filename):
            full_path = '%s/%s' % (repo, obj['path'])
            yield article_details(full_path, obj['sha'])
            count += 1

        if limit is not None and count == limit:
            raise StopIteration


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


def read_article_from_github(path, rendered_text=True):
    """
    Get rendered markdown article text from github API, sha, and github link

    :params path: Path to article (<owner>/<repo>/<dir>/.../article.md>)
    :params rendered_text: Return rendered or raw text
    :returns: (article_text, sha)
    """

    sha = None
    link = None
    text = None

    raw_text, sha, link = article_details_from_github(path)

    if rendered_text:
        text = rendered_markdown_from_github(path)
    else:
        text = raw_text

    return (text, sha, link)


def raw_article_from_github(article):
    """
    Get raw text from github API

    :params article: Article model object
    :returns: article text
    """

    text = None
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

    url = contents_url_from_path(path)
    headers = {'accept': 'application/vnd.github.html'}

    resp = github.get(url, headers=headers)

    if resp.status == 200:
        return resp.data

    return None


def article_details_from_github(path):
    """
    Get article article details from github

    :params path: Path to article (<owner>/<repo>/<dir>/.../article.md>)
    :returns: (raw_text, SHA, github_url)
    """

    text = None
    sha = None
    link = None
    url = contents_url_from_path(path)

    resp = github.get(url)

    if resp.status == 200:
        sha = resp.data['sha']
        link = resp.data['_links']['html']
        text = base64.b64decode(resp.data['content'])

    return (text, sha, link)


def commit_article_to_github(path, message, content, name, email, sha=None):
    """
    Save given article object and content to github

    :params path: Path to article (<owner>/<repo>/<dir>/.../article.md>)
    :params message: Commit message to save article with
    :params content: Content of article
    :params name: Name of author who wrote article
    :params email: Email address of author
    :params sha: Optional SHA of article if it already exists on github

    :returns: HTTP status of API request
    """

    url = contents_url_from_path(path)
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

    resp = github.put(url, data=commit_info, format='json', token=token)

    return resp.status


def read_user_from_github(username=None):
    """
    Read user information from github

    :param username: Optional username to search for, if no username given the
                     currently logged in user will be returned (if any)
    :returns: Dict of information from github API call
    """

    if username is not None:
        resp = github.get('users/%s' % (username))
    else:
        resp = github.get('user')

    if resp.status != 200:
        # FIXME: Handle error
        return {}

    return resp.data


@github.tokengetter
def get_github_oauth_token():
    token = session.get('github_token')
    if token is None:
        # The flask-oauthlib API expects the access token to be in a tuple or a
        # list.  Not exactly sure why since the underlying oauthlib library has a
        # separate kwargs for access_token.  See
        # flask_oauthlib.client.make_client for more information.
        token = (app.config['REPO_OWNER_ACCESS_TOKEN'], )

    return token


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


def contents_url_from_path(path):
    """
    Get github API url for contents of article from full path

    :params path: Path to article (<owner>/<repo>/<dir>/.../article.md>)
    :returns: Url suitable for a content call with github API
    """

    owner, repo, article_path = split_full_article_path(path)
    return 'repos/%s/%s/contents/%s' % (owner, repo, article_path)
