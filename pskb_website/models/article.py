"""
Article related model API
"""

import collections
import copy
import json

from .. import app
from .. import utils
from .. import remote


ARTICLE_FILENAME = 'article.md'
ARTICLE_METADATA_FILENAME = 'details.json'

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
    for file_details in remote.files_from_github(main_article_path(),
                                                 ARTICLE_FILENAME):

        path = parse_full_path(file_details.path)

        # Cannot read this yet
        author_name = None

        yield Article(path.title, author_name, filename=path.filename,
                      repo_path=path.repo, language=path.language,
                      sha=file_details.sha)


def read_article(path, rendered_text=True):
    """
    Read article

    :params path: Short path to article, not including repo or owner
    :returns: Article object
    """

    full_path = '%s/%s' % (main_article_path(), path)
    text, sha, github_url = remote.read_file_from_github(full_path,
                                                         rendered_text)
    if None in (text, sha):
        # FIXME: Handle error here
        return None

    # Parse path to get article information but replace it with improved json
    # meta-data if available.
    details = parse_full_path(full_path)

    author_name = None

    article = Article(details.title, author_name, filename=details.filename,
                      repo_path=details.repo, language=details.language,
                      sha=sha, content=text, external_url=github_url)

    import pdb;pdb.set_trace()
    json_str = read_meta_data_for_article(article)

    if json_str is not None:
        article = Article.from_json(json_str)
        article.content = text
        article.sha = sha

    return article


def save_article(title, path, message, new_content, author_name, email, sha):
    """
    Create or save new article

    :params title: Title of article
    :params path: Short path to article, not including repo or owner, or empty
                  for a new article
    :params message: Commit message to save article with
    :params content: Content of article
    :params author_name: Name of author who wrote article
    :params email: Email address of author
    :params sha: Optional SHA of article if it already exists on github

    :returns: Article object updated or saved
    """

    article = Article(title, author_name)
    if path:
        article.path = path

    status = remote.commit_file_to_github(article.full_path, message,
                                          new_content, author_name, email, sha)
    if status not in (201, 200):
        # FIXME: Handle error
        return None

    status = save_article_meta_data(article, author_name, email)
    if status not in (201, 200):
        # FIXME: Handle error. This is interesting b/c now we created the
        # article, but not the meta data.
        return None

    return read_article(article.path, rendered_text=True)


def save_article_meta_data(article, author_name, email):
    """
    :params article: Article object
    :params name: Name of author who wrote article
    :params email: Email address of author
    :returns: HTTP status of saving meta data
    """
 
    filename = meta_data_path_for_article(article)

    # Get sha of meta data if it exists so we can update it
    text, sha, github_url = remote.read_file_from_github(filename,
                                                         rendered_text=False)
    content = article.to_json()
    message = 'Updating article metadata for %s' % (article.title)

    return remote.commit_file_to_github(filename, message, content,
                                        author_name, email, sha)


def read_meta_data_for_article(article):
    """
    Read meta data for given article

    :params article: Article object
    :returns: Meta-data for article as json
    """

    filename = meta_data_path_for_article(article)
    text, sha, github_url = remote.read_file_from_github(filename,
                                                         rendered_text=False)
    return text


def meta_data_path_for_article(article):
    """
    Get path to meta data file for given article

    :params article: Article object
    :returns: Full path to meta data file for article
    """

    # Last part is the filename, which we're replacing. The meta data file will
    # be stored right next to the article.
    meta_data_path = '/'.join(article.full_path.split('/')[:-1])

    return '%s/%s' % (meta_data_path, ARTICLE_METADATA_FILENAME)


def parse_full_path(path):
    """
    Parse full path and return tuple of details embedded in path

    :params path: Full path to file including repo and owner
    :returns: path_details tuple
    """

    tokens = path.split('/')

    # Repo path is user/repo_name
    repo_path = '/'.join(tokens[:2])

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

    @staticmethod
    def from_json(str_):
        """
        Create article object from json string

        :param str_: json string representing article
        :returns: Article object
        """

        dict_ = json.loads(str_)
        title = dict_.pop('title', None)
        author_name = dict_.pop('author_name', None)

        # This is created dynamically from title
        path = dict_.pop('path', None)

        return Article(title, author_name, **dict_)

    def to_json(self, include_content=False):
        """
        Return json representation of article

        :param include_content: Boolean to include article content in json
                                exported.  This is useful if you're just
                                wanting meta-data and not the 'real' content of
                                an article.

        :returns: json representation of article as a string
        """

        # This is very simple by design. We don't have a lot of crazy nested
        # data here so just do the bare minimum without over-engineering.
        dict_ = copy.deepcopy(self.__dict__)
        if not include_content:
            del dict_['content']

        return json.dumps(dict_)

    @property
    def full_path(self):
        return '%s/%s' % (self.repo_path, self.path)
