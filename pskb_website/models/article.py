"""
Article related model API
"""

import collections

from .. import app
from .. import utils
from .. import remote


ARTICLE_FILENAME = 'article.md'

path_details = collections.namedtuple('path_details',
                                      'repo, language, title, filename')


def main_article_path():
    """Get path to main repo"""

    return '%s/%s' % (app.config['REPO_OWNER'], app.config['REPO_NAME'])


def get_available_articles():
    """Get iterator for current article objects"""

    # Go through the minimal listing of articles and turn it into the full
    # article objects.  This way the github layer only knows what's available
    # on github and doesn't have knowledge of how we organize things, etc.
    for article_details in remote.articles_from_github(main_article_path(),
                                                       ARTICLE_FILENAME):

        path = parse_full_path(article_details.path)

        # Cannot read this yet
        author_name = None

        yield Article(path.title, author_name, filename=path.filename,
                      repo_path=path.repo, language=path.language,
                      sha=article_details.sha)


def read_article(path, rendered_text=True):
    """
    Read article

    :params path: Short path to article, not including repo or owner
    :returns: Article object
    """

    full_path = '%s/%s' % (main_article_path(), path)
    details = parse_full_path(full_path)

    text, sha, github_url = remote.read_article_from_github(full_path,
                                                            rendered_text)
    if None in (text, sha):
        # FIXME: Handle error here
        return None

    author_name = None

    return Article(details.title, author_name, filename=details.filename,
                   repo_path=details.repo, language=details.language, sha=sha,
                   content=text, external_url=github_url)


def save_article(title, path, message, new_content, author_name, email, sha):
    """
    Create or save new article

    :params title: Title of article
    :params path: Short path to article, not including repo or owner, or empty
                  for a new article
    :params message: Commit message to save article with
    :params content: Content of article
    :params name: Name of author who wrote article
    :params email: Email address of author
    :params sha: Optional SHA of article if it already exists on github

    :returns: Article object updated or saved
    """

    article = Article(title, author_name)
    status = remote.commit_article_to_github(article.full_path, message,
                                             new_content, author_name, email,
                                             sha)
    if status not in (201, 200):
        # FIXME: Handle error
        return None

    return read_article(article.path, rendered_text=True)


def parse_full_path(path):
    """
    Parse full path and return tuple of details embedded in path

    :params path: Full path to file including repo and owner
    :returns: path_details tuple
    """

    tokens = path.split('/')

    # Repo path is user/repo_name
    repo_path = '/'.join(tokens[:1])

    # Includes language
    if len(tokens) == 5:
        language = tokens[2]
        title = tokens[3]
        filename = tokens[4]
    else:
        language = None
        title = tokens[2]
        filename = tokens[3]

    return path_details(repo_path, language, title, filename)


class Article(object):
    def __init__(self, title, author_name, filename=ARTICLE_FILENAME,
                 repo_path=None, branch='master', language=None, sha=None,
                 content=None, external_url=None):
        self.title = title
        self.author_name = author_name
        self.language = language
        self.content = content
        self.external_url = external_url

        # Only useful if article has already been saved to github
        self.sha = sha

        self.repo_path = repo_path
        if self.repo_path is None:
            self.repo_path = main_article_path()

        self.branch = branch
        self.filename = filename

        self.path = '%s/%s' % (utils.slugify(self.title), self.filename)

        if self.language is not None:
            self.path = '%s/%s' % (self.language, self.path)

    def __repr__(self):
        return '<author_name: %s title: %s>' % (self.author_name, self.title)

    @property
    def full_path(self):
        return '%s/%s' % (self.repo_path, self.path)
