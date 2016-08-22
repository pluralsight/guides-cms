"""
Main entry point for interacting with remote service APIs
"""

import base64
import collections
import json
import urllib

from flask_oauthlib.client import OAuth
from flask import session

from . import app
from . import cache

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


def default_repo_path():
    """Get path to main repo"""

    return '%s/%s' % (app.config['REPO_OWNER'], app.config['REPO_NAME'])


def default_repo_url():
    """Get URL to default repo"""

    return 'https://github.com/%s/%s' % (app.config['REPO_OWNER'],
                                         app.config['REPO_NAME'])


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

    headers = {}
    cache_key = (repo, sha, filename)
    etag = cache.read_file_listing_etag(cache_key)
    if etag is not None:
        headers = {'If-None-Match': etag}

    resp = _fetch_files_from_github_api(repo, sha, headers=headers)
    if resp is None:
        raise StopIteration

    # Try to read articles from cache
    files = None
    if resp.status == 304:
        try:
            files = _gen_files_from_cache(cache_key, limit=limit)
        except KeyError:
            # Nothing in cache which is odd since we had a etag but that's ok
            # we can do a real read
            pass

    if files is None:
        try:
            files = _gen_files_from_github_api(repo, sha, filename,
                                               limit=limit,
                                               cache_key=cache_key)
        except ValueError:
            raise StopIteration

    for file_ in files:
        yield file_


def _fetch_files_from_github_api(repo, sha, headers=None):
    """
    Grab listing of files from github API

    :param repo: Path to repo (owner/repo_name)
    :param sha: Sha of repo to read with
    :param headers: Optional dict of headers to use in request
    :returns: Response object from request or None if response failed
    """

    url = 'repos/%s/git/trees/%s?recursive=1' % (repo, sha)
    app.logger.debug('GET: %s', url)

    resp = github.get(url, headers=headers)
    if resp.status not in (200, 304):
        log_error('Failed reading files', url, resp)
        return None

    try:
        truncated = resp.data['truncated']
    except KeyError:
        truncated = False

    # FIXME: Handle this scenario
    if truncated:
        log_error('Too many files for API call', url, resp)

    return resp


def _gen_files_from_cache(cache_key, limit=None):
    """
    Get generator through files from cache

    :param cache_key: Key to retrieve files from cache
    :param limit: Optional limit of the number of files to return

    :returns: Iterator through file_details tuples
    :raises: KeyError if cache is a miss
    """

    files = cache.read_file_listing(cache_key)
    if files is None:
        raise KeyError('No files found with %s' % (cache_key))

    count = 0
    for file_ in json.loads(files):
        yield file_details(file_[0], None, file_[1], None, None, None)
        count += 1

        if limit is not None and count == limit:
            raise StopIteration


def _gen_files_from_github_api(repo, sha, filename, limit=None, cache_key=None):
    """
    Iterate through files with a specific name from github and cache files if
    cache_key is given

    :param repo: Path to repo to read files from
    :param sha: Sha of repo to read with
    :param filename: Name of filename to search for recursively
    :param limit: Optional limit of the number of files to return
    :param cache_key: Optional key to cache file listing with

    :returns: Iterator through file_details tuples or None if request fails
    """

    resp = _fetch_files_from_github_api(repo, sha)
    if resp is None:
        raise ValueError('Failed reponse')

    count = 0
    files = []

    for obj in resp.data['tree']:
        if obj['path'].endswith(filename):
            full_path = '%s/%s' % (repo, obj['path'])
            yield file_details(full_path, None, obj['sha'], None, None, None)
            count += 1

            if cache_key is not None:
                # Easier to serialize a standard tuple than namedtuple
                files.append((full_path, obj['sha']))

        if limit is not None and count == limit:
            break

    if files and cache_key:
        cache.save_file_listing(cache_key, json.dumps(files))


def repo_sha_from_github(repo, branch=u'master'):
    """
    Get sha from head of given repo

    :param repo: Path to repo (owner/repo_name)
    :param branch: Name of branch to get sha for
    :returns: Sha of branch
    """

    url = 'repos/%s/git/refs/heads/%s' % (repo, branch)
    app.logger.debug('GET: %s', url)

    resp = github.get(url)

    if resp.status != 200:
        log_error('Failed reading sha', url, resp, branch=branch)
        return None

    return resp.data['object']['sha']


def primary_github_email_of_logged_in():
    """Get primary email address of logged in user"""

    app.logger.debug('GET: user/emails')

    resp = github.get('user/emails')
    if resp.status != 200:
        return None

    for email_data in resp.data:
        if email_data['primary']:
            return email_data['email']

    return None


def read_file_from_github(path, branch=u'master', rendered_text=True,
                          allow_404=False):
    """
    Get rendered file text from github API

    :param path: Path to file (<owner>/<repo>/<dir>/.../<filename>)
    :param branch: Name of branch to read file from
    :param rendered_text: Return rendered or raw text
    :param allow_404: False to log warning for 404 or True to allow it i.e.
                      when you're just seeing if a file already exists
    :returns: file_details namedtuple or None if error

    Note when requesting rendered text there will be no SHA or last_updated
    data available.  This is a restriction from the github API
    (https://developer.github.com/v3/media/#repository-contents) Requesting
    file 'details' like SHA and rendered text are 2 API calls.  Therefore, if
    you want all of that information you should call this function twice, once
    with rendered_text=True and one with rendered_text=False and combine the
    information yourself.
    """

    if rendered_text:
        text = rendered_markdown_from_github(path, branch, allow_404=allow_404)

        # This is a little tricky b/c this URL could change on github and we
        # would be wrong.  However, those URLs have been the same for years so
        # seems like a safe enough bet at this point.
        owner, repo, file_path = split_full_file_path(path)

        # Cannot pass unicode data to pathname2url or it can raise KeyError.
        # Must only pass URL-safe bytes. So, something like u'\u2026' will
        # raise a # KeyError but if we encode it to bytes, '%E2%80%A6', things
        # work correctly.
        # http://stackoverflow.com/questions/15115588/urllib-quote-throws-keyerror

        url = u'https://github.com/%s/%s/blob/%s/%s' % (
                owner,
                repo,
                branch,
                urllib.pathname2url(file_path.encode('utf-8')))

        details = file_details(path, branch, None, None, url, text)
    else:
        details = file_details_from_github(path, branch, allow_404=allow_404)

    return details


def rendered_markdown_from_github(path, branch=u'master', allow_404=False):
    """
    Get rendered markdown file text from github API

    :param path: Path to file (<owner>/<repo>/<dir>/.../<filename.md>)
    :param branch: Name of branch to read file from
    :param allow_404: False to log warning for 404 or True to allow it i.e.
                      when you're just seeing if a file already exists
    :returns: HTML file text
    """

    url = contents_url_from_path(path)
    headers = {'accept': 'application/vnd.github.html'}
    app.logger.debug('GET: %s, headers: %s, ref: %s', url, headers, branch)

    resp = github.get(url, headers=headers, data={'ref': branch})
    if resp.status == 200:
        return unicode(resp.data, encoding='utf-8')

    if resp.status != 404 or not allow_404:
        log_error('Failed reading rendered markdown', url, resp, branch=branch)

    return None


def file_details_from_github(path, branch=u'master', allow_404=False):
    """
    Get file details from github

    :param path: Path to file (<owner>/<repo>/<dir>/.../<filename>)
    :param branch: Name of branch to read file from
    :param allow_404: False to log warning for 404 or True to allow it i.e.
                      when you're just seeing if a file already exists
    :returns: file_details namedtuple or None for error
    """

    url = contents_url_from_path(path)
    app.logger.debug('GET: %s ref: %s', url, branch)

    resp = github.get(url, data={'ref': branch})

    if resp.status == 200:

        # Temporary debug. It seems that sometimes github returns a 200
        # response and a list of items, which should only happen if we ask for
        # the contents of a directory.  This function should never be called
        # with a directory.
        try:
            sha = resp.data['sha']
        except TypeError as err:
            app.logger.error('Incorrect SHA response for URL: %s, resp: %s, err: %s',
                             url, resp.data, err)
            return None

        link = resp.data['_links']['html']
        text = unicode(base64.b64decode(resp.data['content'].encode('utf-8')),
                       encoding='utf-8')
        last_updated = resp._resp.headers.get('Last-Modified')
    else:
        if resp.status != 404 or (resp.status == 404 and not allow_404):
            app.logger.warning('Failed reading file details at "%s", status: %d, branch: %s, data: %s',
                               url, resp.status, branch, resp.data)

        return None

    return file_details(path, branch, sha, last_updated, link, text)


def commit_file_to_github(path, message, content, name, email, sha=None,
                          branch=u'master', auto_encode=True):
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
    :param auto_encode: Boolean to automatically encode data as utf-8

    :returns: SHA of commit or None for failure

    Note that name and email can be None if you want to make a commit with the
    REPO_OWNER.  However, name and email should both exist or both be None,
    which is a requirement of the underlying Github API.
    """

    url = contents_url_from_path(path)

    if auto_encode:
        content = base64.b64encode(content.encode('utf-8'))

    commit_info = {'message': message, 'content': content, 'branch': branch}

    if name is not None and email is not None:
        commit_info['author'] = {'name': name, 'email': email}
        commit_info['committer'] = {'name': name, 'email': email}
    elif (name is None and email is not None) or (name is not None and email is None):
        raise ValueError('Must specify both name and email or neither')

    if sha:
        commit_info['sha'] = sha

    # The flask-oauthlib API expects the access token to be in a tuple or a
    # list.  Not exactly sure why since the underlying oauthlib library has a
    # separate kwargs for access_token.  See flask_oauthlib.client.make_client
    # for more information.
    token = (app.config['REPO_OWNER_ACCESS_TOKEN'], )

    app.logger.debug('PUT: %s, data: %s, token: %s', url, commit_info, token)

    resp = github.put(url, data=commit_info, format='json', token=token)

    if resp.status not in (201, 200):
        log_error('Failed saving file', url, resp, commit_msg=message,
                  content=content, name=name, email=email, sha=sha,
                  branch=branch)
        return None

    return resp.data['commit']['sha']


def commit_image_to_github(path, message, file_, name, email, sha=None,
                           branch=u'master'):
    """
    Save given image file content to github

    :param path: Path to file (<owner>/<repo>/<dir>/.../<filename>)
    :param message: Commit message to save file with
    :param file_: Open file object
    :param name: Name of author who wrote file
    :param email: Email address of author
    :param sha: Optional SHA of file if it already exists on github
    :param branch: Name of branch to commit file to (branch must already
                   exist)

    :returns: SHA of commit or None for failure
    """

    contents = base64.encodestring(file_.read())
    return commit_file_to_github(path, message, contents, name, email, sha=sha,
                                 branch=branch, auto_encode=False)


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

    app.logger.debug('GET: %s', url)

    resp = github.get(url)

    if resp.status != 200:
        log_error('Failed reading user', url, resp)
        return {}

    return resp.data


def read_repo_collaborators_from_github(owner=None, repo=None):
    """
    Generator for collaborator login/usernames for a given repo

    :param owner: Owner of repository defaults to REPO_OWNER config value
    :param repo: Name of repository defaults to REPO_NAME config value
    :returns: Generator through login names
    """

    owner = owner or app.config['REPO_OWNER']
    repo = repo or app.config['REPO_NAME']

    url = '/repos/%s/%s/collaborators' % (owner, repo)

    # This endpoint requires a user that has push access
    token = (app.config['REPO_OWNER_ACCESS_TOKEN'], )

    app.logger.debug('GET: %s, token: %s', url, token)

    resp = github.get(url, token=token)

    if resp.status != 200:
        log_error('Failed reading collaborators', url, resp, repo=repo,
                  owner=owner)
        raise StopIteration

    for obj in resp.data:
        yield obj['login']


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
    :returns: URL suitable for a content call with github API
    """

    owner, repo, file_path = split_full_file_path(path)

    # Cannot pass unicode data to pathname2url or it can raise KeyError. Must
    # only pass URL-safe bytes. So, something like u'\u2026' will raise a
    # KeyError but if we encode it to bytes, '%E2%80%A6', things work
    # correctly.
    # http://stackoverflow.com/questions/15115588/urllib-quote-throws-keyerror
    owner = owner.encode('utf-8')
    repo = repo.encode('utf-8')
    file_path = file_path.encode('utf-8')

    return urllib.pathname2url('repos/%s/%s/contents/%s' % (owner, repo,
                                                            file_path))


def read_branch(repo_path, name):
    """
    Read branch and get HEAD sha

    :param repo_path: Path to repo of branch
    :param name: Name of branch to read
    :returns: SHA of HEAD or None if branch is not found
    """

    url = 'repos/%s/git/refs/heads/%s' % (repo_path, name)

    app.logger.debug('GET: %s', url)

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

    app.logger.debug('POST: %s, data: %s, token: %s', url, data, token)

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

    app.logger.debug('PATCH: %s, data: %s, token: %s', url, data, token)

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
    app.logger.debug('GET: %s', url)

    resp = github.get(url)
    if resp.status != 200:
        log_error('Failed checking rate limit', url, resp)
        return None

    return resp.data


def remove_file_from_github(path, message, name, email, branch):
    """
    Remove file from github repo

    :param path: Path to file (<owner>/<repo>/<dir>/.../<filename>)
    :param message: Commit message to remove file with
    :param name: Name of author who wrote file
    :param email: Email address of author
    :param branch: Name of branch to delete file from
    :returns: True if file was removed or False otherwise

    Note the file is only removed from the repository, not the history of the
    file.
    """

    # Read most recent sha which is required to remove file
    details = file_details_from_github(path, branch)
    if details is None:
        return False

    url = contents_url_from_path(path)
    commit_info = {'sha': details.sha, 'branch': branch, 'message': message,
                   'author': {'name': name, 'email': email},
                   'committer': {'name': name, 'email': email}}

    # The flask-oauthlib API expects the access token to be in a tuple or a
    # list.  Not exactly sure why since the underlying oauthlib library has a
    # separate kwargs for access_token.  See flask_oauthlib.client.make_client
    # for more information.
    token = (app.config['REPO_OWNER_ACCESS_TOKEN'], )

    app.logger.debug('DELETE: %s, data: %s, token: %s', url, commit_info, token)

    resp = github.delete(url, data=commit_info, format='json', token=token)
    if resp.status != 200:
        log_error('Failed removing file', url, resp, file=path)
        return False

    return True


def merge_branch(repo_path, base, head, message):
    """
    Attempt merge between two branches

    :param repo_path: Path to repo <owner>/<repo_name>
    :param base: Name of the base branch that the head will be merged into
    :param head: The name of the head to merge into base
    :param message: Commit message to use for merge
    :returns: True if merge was successful False otherwise
    """

    url = '/repos/%s/merges' % (repo_path)
    data = {'base': base, 'head': head, 'commit_message': message}

    token = (app.config['REPO_OWNER_ACCESS_TOKEN'], )

    app.logger.debug('POST: %s, data: %s, token: %s', url, data, token)

    resp = github.post(url, data=data, format='json', token=token)

    # 204 means no content i.e. no merge needed
    if resp.status in (201, 204):
        return True

    log_error('Failed merging', url, resp, repo=repo_path, base=base, head=head)
    return False


def file_contributors(path, branch=u'master'):
    """
    Get dictionary of User objects representing authors and committers to a
    file

    :param path: Short-path to file (<dir>/.../<filename>) i.e. without repo
                 and owner
    :param base: Name of branch to read contributors for
    :returns: Dictionary of the following form::

        {'authors': set([(name, login), (name, login), ...]),
         'committers': set([(name, login), (name, login), ...])}

    Note that name can be None if user doesn't have their full name setup on
    github account.
    """

    contribs = {'authors': set(), 'committers': set()}
    url = u'/repos/%s/commits' % (default_repo_path())

    app.logger.debug('GET: %s path: %s, branch: %s', url, path, branch)

    resp = github.get(url, data={'path': path, 'branch': branch})
    if resp.status != 200:
        log_error('Failed reading commits from github', url, resp)
        return contribs

    def _extract_data_from_commit(commit, key):
        login = commit[key]['login']

        try:
            author_name = commit['commit'][key]['name']
        except KeyError:
            author_name = None
        else:
            if not author_name:
                author_name = None

        # API can return same name and login depending on how the account and
        # commit information is setup so don't bother storing duplicates. This
        # way caller knows we didn't get a real author name.
        if login == author_name:
            author_name = None

        return (author_name, commit[key]['login'])

    for commit in resp.data:
        # Check author/committer first b/c we've seen issues in github API
        # where these can actually be None, like this commit:
        # https://github.com/pluralsight/guides/commit/44cd2072df8994fea2cee9de6ffb6c174b57bf03
        if commit['author']:
            contribs['authors'].add(_extract_data_from_commit(commit, 'author'))

        if commit['committer']:
            contribs['committers'].add(_extract_data_from_commit(commit, 'committer'))

    return contribs


def contributor_stats(repo_path=None):
    """
    Get response of /repos/<repo_path>/stats/contributors from github.com

    :param repo_path: Default repo or repo path in owner/repo_name form
    :returns: Raw response of contributor stats from https://developer.github.com/v3/repos/statistics/#get-contributors-list-with-additions-deletions-and-commit-counts

    Note the github caches contributor results so an empty list can also be
    returned if the data is not available yet or there is an error
    """

    repo_path = default_repo_path() if repo_path is None else repo_path
    url = u'/repos/%s/stats/contributors' % (repo_path)

    app.logger.debug('GET: %s', url)

    resp = github.get(url)

    stats = []
    if resp.status == 200:
        stats = resp.data
    elif resp.status == 202:
        app.logger.info('Data not in cache from github.com')
    else:
        log_error('Failed reading stats from github', url, resp)

    return stats
