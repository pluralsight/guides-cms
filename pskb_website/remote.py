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

file_details = collections.namedtuple('file_details', 'path, branch, sha, last_updated, url, text')


def log_error(message, url, resp, **kwargs):
    """
    Log an error from a request and include URL, response status, response data
    and additional error information

    :params message: Message to log
    :param url: URL of request that failed
    :param resp: Response object holding failure information
    :param kwargs: Additional data to put in error message
    :returns: None
    """

    additional_info = []
    if kwargs:
        for key, value in kwargs.iteritems():
            additional_info.append('%s: "%s"' % (key, value))

    app.logger.error('%s at "%s", status: %d, data: %s, %s',
                     message, url, resp.status, getattr(resp, 'data', None),
                     ','.join(additional_info))


def files_from_github(repo, filename, limit=None):
    """
    Iterate through files with a specific name from github

    :param repo: Path to repo to read files from
    :param filename: Name of filename to search for recursively
    :param limit: Optional limit of the number of files to return

    :returns: Iterator through file_details tuples
    """

    sha = repo_sha_from_github(repo)
    if sha is None:
        raise StopIteration

    url = 'repos/%s/git/trees/%s?recursive=1' % (repo, sha)
    resp = github.get(url)

    if resp.status != 200:
        log_error('Failed reading files', url, resp)
        raise StopIteration

    # FIXME: Handle this scenario
    if resp.data['truncated']:
        log_error('Too many files for API call', url, resp)

    count = 0
    for obj in resp.data['tree']:
        if obj['path'].endswith(filename):
            full_path = '%s/%s' % (repo, obj['path'])
            yield file_details(full_path, None, obj['sha'], None, None, None)
            count += 1

        if limit is not None and count == limit:
            raise StopIteration


def repo_sha_from_github(repo, branch='master'):
    """
    Get sha from head of given repo

    :param repo: Path to repo (owner/repo_name)
    :param branch: Name of branch to get sha for
    :returns: Sha of branch
    """

    url = 'repos/%s/git/refs/heads/%s' % (repo, branch)
    resp = github.get(url)

    if resp.status != 200:
        log_error('Failed reading sha', url, resp, branch=branch)
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


def read_file_from_github(path, branch='master', rendered_text=True):
    """
    Get rendered file text from github API

    :param path: Path to file (<owner>/<repo>/<dir>/.../<filename>)
    :param branch: Name of branch to read file from
    :param rendered_text: Return rendered or raw text
    :returns: file_details namedtuple or None if error
    """

    details = file_details_from_github(path, branch)

    if rendered_text:
        text = rendered_markdown_from_github(path, branch)
        details = file_details(path, branch, details.sha, details.last_updated,
                               details.url, text)

    return details


def rendered_markdown_from_github(path, branch='master'):
    """
    Get rendered markdown file text from github API

    :param path: Path to file (<owner>/<repo>/<dir>/.../<filename.md>)
    :param branch: Name of branch to read file from
    :returns: HTML file text
    """

    url = contents_url_from_path(path)
    headers = {'accept': 'application/vnd.github.html'}

    resp = github.get(url, headers=headers, data={'ref': branch})
    if resp.status == 200:
        return unicode(resp.data, encoding='utf-8')

    log_error('Failed reading rendered markdown', url, resp, branch=branch)

    return None


def file_details_from_github(path, branch='master'):
    """
    Get file details from github

    :param path: Path to file (<owner>/<repo>/<dir>/.../<filename>)
    :param branch: Name of branch to read file from
    :returns: file_details namedtuple or None for error
    """

    url = contents_url_from_path(path)
    resp = github.get(url, data={'ref': branch})

    if resp.status == 200:
        sha = resp.data['sha']
        link = resp.data['_links']['html']
        text = unicode(base64.b64decode(resp.data['content'].encode('utf-8')),
                       encoding='utf-8')
        last_updated = resp._resp.headers.get('Last-Modified')
    else:
        app.logger.warning('Failed reading file details at "%s", status: %d, data: %s',
                           url, resp.status, resp.data)

        return None

    return file_details(path, branch, sha, last_updated, link, text)


def commit_file_to_github(path, message, content, name, email, sha=None,
                          branch='master'):
    """
    Save given file content to github

    :param path: Path to file (<owner>/<repo>/<dir>/.../<filename>)
    :param message: Commit message to save file with
    :param content: Content of file
    :param name: Name of author who wrote file
    :param email: Email address of author
    :param sha: Optional SHA of file if it already exists on github
    :param branch: Name of branch to commit file to (branch must already
                   exist)

    :returns: True if data was saved, False otherwise
    """

    url = contents_url_from_path(path)
    content = base64.b64encode(content.encode('utf-8'))
    commit_info = {'message': message, 'content': content, 'branch': branch,
                   'author': {'name': name, 'email': email}}

    if sha:
        commit_info['sha'] = sha

    # The flask-oauthlib API expects the access token to be in a tuple or a
    # list.  Not exactly sure why since the underlying oauthlib library has a
    # separate kwargs for access_token.  See flask_oauthlib.client.make_client
    # for more information.
    token = (app.config['REPO_OWNER_ACCESS_TOKEN'], )

    resp = github.put(url, data=commit_info, format='json', token=token)

    if resp.status not in (201, 200):
        log_error('Failed saving file', url, resp, commit_msg=message,
                  content=content, name=name, email=email, sha=sha,
                  branch=branch)
        return False

    return True


def read_user_from_github(username=None):
    """
    Read user information from github

    :param username: Optional username to search for, if no username given the
                     currently logged in user will be returned (if any)
    :returns: Dict of information from github API call
    """

    if username is not None:
        url = 'users/%s' % (username)
    else:
        url = 'user'

    resp = github.get(url)

    if resp.status != 200:
        log_error('Failed reading user', url, resp)
        return {}

    return resp.data


@github.tokengetter
def get_github_oauth_token():
    """Read github token from session"""

    token = session.get('github_token')
    if token is None:
        # The flask-oauthlib API expects the access token to be in a tuple or a
        # list.  Not exactly sure why since the underlying oauthlib library has a
        # separate kwargs for access_token.  See
        # flask_oauthlib.client.make_client for more information.
        token = (app.config['REPO_OWNER_ACCESS_TOKEN'], )

    return token


def split_full_file_path(path):
    """
    Split full file path into owner, repo, and file_path

    :param path: Path to file (<owner>/<repo>/<dir>/.../<filename>)
    :returns: (owner, repo, file_path)
    """

    tokens = path.split('/')

    owner = tokens[0]
    repo = tokens[1]
    file_path = '/'.join(tokens[2:])

    return (owner, repo, file_path)


def contents_url_from_path(path):
    """
    Get github API url for contents of file from full path

    :param path: Path to file (<owner>/<repo>/<dir>/.../<filename>)
    :returns: Url suitable for a content call with github API
    """

    owner, repo, file_path = split_full_file_path(path)
    return 'repos/%s/%s/contents/%s' % (owner, repo, file_path)


def read_branch(repo_path, name):
    """
    Read branch and get HEAD sha

    :param repo_path: Path to repo of branch
    :param name: Name of branch to read
    :returns: SHA of HEAD or None if branch is not found
    """

    url = 'repos/%s/git/refs/heads/%s' % (repo_path, name)
    resp = github.get(url)

    # Branch doesn't exist
    if resp.status == 404:
        return None

    if resp.status != 200:
        log_error('Failed reading branch', url, resp)
        return None

    return resp.data['object']['sha']


def create_branch(repo_path, name, sha):
    """
    Create a new branch

    :param repo_path: Path to repo that branch should be created from
    :param name: Name of branch to create
    :param sha: SHA to branch from
    :returns: True if branch was created or False if branch already exists or
              could not be created
    """

    url = 'repos/%s/git/refs' % (repo_path)
    data = {'ref': 'refs/heads/%s' % (name), 'sha': sha}

    # Must use token of owner for this request b/c only owners and
    # collaborators can create branches
    token = (app.config['REPO_OWNER_ACCESS_TOKEN'], )
    resp = github.post(url, data=data, format='json', token=token)

    if resp.status == 422:
        # Maybe it already exists
        curr_sha = read_branch(repo_path, name)
        if curr_sha is not None:
            return True

        log_error('Failed reading existing branch', url, resp, sha=sha)

        return False

    elif resp.status != 201:
        log_error('Failed creating branch', url, resp, sha=sha)
        return False

    return True


def update_branch(repo_path, name, sha):
    """
    Update branch to new commit SHA

    :param repo_path: Path to repo that branch should be created from
    :param name: Name of branch to create
    :param sha: SHA to branch from
    :returns: True if branch was update or False if branch could not be updated
    """

    url = 'repos/%s/git/refs/heads/%s' % (repo_path, name)
    data = {'sha': sha}

    # Must use token of owner for this request b/c only owners and
    # collaborators can update branches
    token = (app.config['REPO_OWNER_ACCESS_TOKEN'], )
    resp = github.patch(url, data=data, format='json', token=token)
    if resp.status != 200:
        log_error('Failed updating branch', url, resp, sha=sha)
        return False

    return True


def check_rate_limit():
    """
    Get rate limit data

    :returns: None in case of an error or raw rate limit request data
    """

    url = '/rate_limit'
    resp = github.get(url)
    if resp.status != 200:
        log_error('Failed checking rate limit', url, resp)
        return None

    return resp.data
