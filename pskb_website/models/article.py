"""
Article related model API
"""

import collections
import json

from .. import app
from .. import cache
from . import lib
from .. import remote
from .. import utils


# FIXME: This file is fairly modular to the outside world but internally it's
# very fragmented and the layers of abstraction are all mixed up.  Needs a lot
# of TLC...


FILE_EXTENSION = '.md'
ARTICLE_FILENAME = 'article%s' % (FILE_EXTENSION)
ARTICLE_METADATA_FILENAME = 'details.json'

path_details = collections.namedtuple('path_details', 'repo, filename')


def main_article_path():
    """Get path to main repo"""

    return '%s/%s' % (app.config['REPO_OWNER'], app.config['REPO_NAME'])


def get_available_articles(published=None, repo_path=None):
    """
    Get iterator for current article objects

    :param published: True for only published articles, False for only drafts
                      or None for all articles
    :param repo_path: Optional repo path to read from (<owner>/<name>)

    :returns: Iterator through article objects

    Note that article objects only have path, title and author name filled out.
    You'll need to call read_article() to get full article details.
    """

    # Go through the minimal listing of articles and turn it into the full
    # article objects.  This way the github layer only knows what's available
    # on github and doesn't have knowledge of how we organize things, etc.
    if repo_path is None:
        repo_path = main_article_path()

        if published:
            files = cache.read_file_listing('published')
            if files is not None:
                for json_str in json.loads(files):
                    try:
                        yield Article.from_json(json_str)
                    except ValueError:
                        app.logger.error('Failed parsing json meta data from cache "%s"',
                                         json_str)
                        continue

                raise StopIteration

    files_to_cache = []

    for file_details in remote.files_from_github(repo_path, ARTICLE_FILENAME):
        # We're only caching published articles right now so don't waste a
        # roundtrip to cache if that's not what caller wants.
        article = None

        if published:
            article = read_article_from_cache(file_details.path)

        if article is None:
            path_info = parse_full_path(file_details.path)
            json_str = read_meta_data_for_article_path(file_details.path)
            if json_str is None:
                # Cannot do anything here b/c we do not know the title.
                app.logger.error('Failed reading meta data for "%s", file_details: %s',
                                 path_info, file_details)
                continue

            try:
                article = Article.from_json(json_str)
            except ValueError:
                app.logger.error('Failed parsing json meta data for "%s", file_details: %s, json: %s',
                                 path_info, file_details, json_str)
                continue

            article.filename = path_info.filename
            article.repo_path = path_info.repo

        if published is None or article.published == published:
            yield article

        if published and article.published:
            files_to_cache.append(lib.to_json(article))

    if files_to_cache:
        cache.save_file_listing('published', json.dumps(files_to_cache))


def get_articles_for_author(author_name, published=None):
    """
    Get iterator for articles from given author

    :param author_name: Name of author to find articles for
    :param published: True for only published articles, False for only drafts
                      or None for all articles
    :returns: Iterator through article objects
    """

    for article in get_available_articles(published=published):
        if article.author_name == author_name:
            yield article


def read_article(path, rendered_text=True, branch='master', repo_path=None):
    """
    Read article

    :param path: Short path to article, not including repo or owner
    :param rendered_text: Boolean to read rendered or raw text
    :param branch: Name of branch to read file from
    :param repo_path: Optional repo path to read from (<owner>/<name>)

    :returns: Article object
    """

    if repo_path is None:
        repo_path = main_article_path()

    full_path = '%s/%s' % (repo_path, path)

    # Handle scenario where caller forgets to include filename, default it
    if not path.endswith(FILE_EXTENSION):
        slash = '' if path.endswith('/') else '/'
        full_path = '%s%s%s' % (full_path, slash, ARTICLE_FILENAME)

    # Only caching rendered text of articles since that's the 'front-end' of
    # the site.
    if rendered_text:
        article = read_article_from_cache(path, branch)
        if article is not None:
            return article

    details = remote.read_file_from_github(full_path, branch, rendered_text)
    if details is None or None in (details.text, details.sha):
        app.logger.error('Failed reading path: "%s" branch: %s', full_path,
                         branch)
        return None

    # Parse path to get article information but replace it with improved json
    # meta-data if available.
    path_info = parse_full_path(full_path)
    json_str = read_meta_data_for_article_path(full_path)

    if json_str is not None:
        article = Article.from_json(json_str)

        # Update it with what we pull from the article file and path
        article.content = details.text
        article.sha = details.sha
        article.external_url = details.url
        article.filename = path_info.filename
        article.repo_path = path_info.repo
        article.branch = branch
        article.last_updated = details.last_updated

        # We don't have a ton of cache space so reserve it for more
        # high-traffic data like published articles.
        if article.published:
            cache.save_article(article.path, article.branch,
                               lib.to_json(article))
    else:
        # We cannot properly show an article without metadata.
        article = None
        app.logger.error('Failed reading meta data for %s, full_path: %s, branch: %s',
                         path_info, full_path, branch)

    return article


def read_article_from_cache(path, branch='master'):
    """
    Read article object from cache

    :param path: Path to read file from github i.e. path it was cached with
    :param branch: Branch to read file from
    :returns: Article object if found in cache or None
    """

    if path.endswith(FILE_EXTENSION):
        # Don't cache with the filename b/c it just takes up cache space and
        # right now it's always the same.
        path = path.split('/')[-2]

    json_str = cache.read_article(path, branch)
    if json_str is None:
        return None

    return Article.from_json(json_str)


def save_article(title, path, message, new_content, author_name, email, sha,
                 branch='master', image_url=None, repo_path=None,
                 author_real_name=None, stacks=None):
    """
    Create or save new (original) article, not branched article

    :param title: Title of article
    :param path: Short path to article, not including repo or owner, or empty
                  for a new article
    :param message: Commit message to save article with
    :param content: Content of article
    :param author_name: Name of author who wrote article
    :param email: Email address of author
    :param sha: Optional SHA of article if it already exists on github
    :param branch: Name of branch to commit file to (branch must already
                   exist)
    :param image_url: Image to use for article
    :param repo_path: Optional repo path to save into (<owner>/<name>)
    :param author_real_name: Optional real name of author, not username
    :param stacks: Optional list of stacks to associate with article

    :returns: Article object updated or saved

    This function is not suitable for saving branched articles.  The article
    created here will be attributed to the given author_name whereas branched
    articles should be created with branch_article() so the correct author
    information is maintained.
    """

    article = Article(title, author_name, branch=branch, image_url=image_url,
                      repo_path=repo_path, author_real_name=author_real_name,
                      stacks=stacks)
    if path:
        article.path = path

    saved = remote.commit_file_to_github(article.full_path, message,
                                         new_content, author_name, email, sha,
                                         branch)
    if not saved:
        return None

    if branch != 'master':
        saved = save_branched_article_meta_data(article, author_name, email)
    else:
        saved = save_article_meta_data(article, author_name, email, branch)

    if not saved:
        # FIXME: Handle error. This is interesting b/c now we created the
        # article, but not the meta data.
        return None

    return read_article(article.path, rendered_text=True,
                        branch=article.branch, repo_path=repo_path)


def branch_article(article, message, new_content, author_name, email,
                   image_url, author_real_name=None):
    """
    Create branch for article with new article contents

    :param article: Article object to branch
    :param message: Message describing article suggestions/changes
    :param new_content: New article text
    :param author_name: Name of author for article changes
    :param email: Email of author for article changes
    :param image_url: Image to use for article
    :param author_real_name: Optional real name of author, not username

    :returns: New article object

    New branch will be named after author of changes
    """

    branch = author_name

    # Create branch if we needed to
    repo_sha = remote.read_branch(article.repo_path, branch)
    if repo_sha is None:
        repo_sha = remote.read_branch(article.repo_path, 'master')
        if repo_sha is None:
            app.logger.error('Cannot find master branch "%s"',
                             article.repo_path)
            return None

        if not remote.create_branch(article.repo_path, branch, repo_sha):
            return None

    return save_article(article.title, article.path, message, new_content,
                        author_name, email, article.sha, branch=branch,
                        image_url=image_url, author_real_name=author_real_name,
                        stacks=article.stacks)


def branch_or_save_article(title, path, message, content, author_name, email,
                           sha, image_url, repo_path=None,
                           author_real_name=None, stacks=None):
    """
    Save article as original or as a branch depending on if given author is
    the same as original article (if it already exists)

    :param title: Title of article
    :param path: Short path to article, not including repo or owner, or empty
                  for a new article
    :param message: Commit message to save article with
    :param content: Content of article
    :param author_name: Name of author who wrote content
    :param email: Email address of author
    :param sha: Optional SHA of article if it already exists on github
    :param branch: Name of branch to commit file to (branch must already
                    exist)
    :param image_url: Image to use for article
    :param repo_path: Optional repo path to save into (<owner>/<name>)
    :param author_real_name: Optional real name of author, not username
    :param stacks: Optional list of stacks to associate with article (this
                   argument is ignored if article is branched)

    :returns: Article object updated, saved, or branched
    """

    if path:
        article = read_article(path, rendered_text=False, branch='master',
                               repo_path=repo_path)
    else:
        article = None

    if article and article.author_name != author_name and sha:
        # Note branching an article cannot change the stacks!
        new = branch_article(article, message, content, author_name, email,
                             image_url, author_real_name=author_real_name)
    else:
        new = save_article(title, path, message, content, author_name, email,
                           sha, image_url=image_url, repo_path=repo_path,
                           author_real_name=author_real_name,
                           stacks=stacks)

    return new


def save_article_meta_data(article, author_name, email, branch=None):
    """
    :param article: Article object
    :param author_name: Name of author who wrote article
    :param email: Email address of author
    :param branch: Optional branch to save metadata, if not given
                   article.branch will be used
    :returns: True if meta data is saved, False otherwise
    """

    filename = meta_data_path_for_article_path(article.full_path)

    if branch is None:
        branch = article.branch

    # Get sha of meta data if it exists so we can update it if it already
    # exists
    details = remote.read_file_from_github(filename, rendered_text=False,
                                           branch=branch)
    sha = None
    if details is not None:
        sha = details.sha

    # Don't need to serialize everything, just the important stuff that's not
    # stored in the path and article.
    exclude_attrs = ('content', 'external_url', 'sha', 'repo_path', 'path',
                     'last_updated')
    json_content = lib.to_json(article, exclude_attrs=exclude_attrs)

    message = 'Updating article metadata for %s' % (article.title)

    # Article is on a branch so we have to update the master meta data file
    # with this new branch as well as the branch meta data file.

    return remote.commit_file_to_github(filename, message, json_content,
                                        author_name, email, sha, branch=branch)


def read_meta_data_for_article_path(full_path):
    """
    Read meta data for given article path from master branch

    :param full_path: Full path to article
    :returns: Meta-data for article as json

    Always read meta data from master branch because metadata is never altered
    or updated in branches to keep merging simple.
    """

    filename = meta_data_path_for_article_path(full_path)
    details = remote.read_file_from_github(filename, rendered_text=False)
    if details is None:
        return None

    return details.text


def meta_data_path_for_article_path(full_path):
    """
    Get path to meta data file for given article path

    :param full_path: Article object
    :returns: Full path to meta data file for article
    """

    # Last part is the filename, which we're replacing. The meta data file will
    # be stored right next to the article.
    meta_data_path = '/'.join(full_path.split('/')[:-1])

    return '%s/%s' % (meta_data_path, ARTICLE_METADATA_FILENAME)


def save_branched_article_meta_data(article, author_name, email,
                                    add_branch=True):
    """
    Save metadata for branched article

    :param article: Article object with branch attribute set to branch name
    :param name: Name of author who wrote branched article
    :param email: Email address of branched article author
    :param add_branch: True if article should be saved as a branch False if
                       article should be removed as a branch
    :returns: True if data is saved, False otherwise

    Metadata for branched articles should be identical to the original article.
    This makes it easier for automatically merging changes because metadata
    differences won't get in the way.  The author_name is the only thing useful
    for a branched article.  However, that should already be encoded in the
    branch name and the commits.  So, editors of original articles will get
    credit for helping via those mechanisms, not metadata.
    """

    orig_article = read_article(article.path, rendered_text=False,
                                branch='master', repo_path=article.repo_path)

    # Nothing to save, we're already tracking this branch
    if add_branch:
        if article.branch in orig_article.branches:
            return True

        orig_article.branches.append(article.branch)
    else:
        try:
            orig_article.branches.remove(article.branch)
        except ValueError:
            # Branch isn't being tracked anyway so nothing to remove
            return True

    # Note we don't ever change metadata on the branches. This keeps the
    # metadata from showing in up in merges. We only want to deal with article
    # text for merges.
    return save_article_meta_data(orig_article, author_name, email)


def delete_article(article, message, name, email):
    """
    Delete article from repository

    :param article: Article object to remove
    :param message: Message to include as commit when removing article
    :param name: Name of user deleting article
    :param email: Email address of user deleting article
    :returns: True if article was successfully removed or False otherwise

    This removes the article from the repository but not the history of
    the file.

    Only original author can remove file from master branch.  Articles can be
    removed from non-master branches only by the user who created that branch.
    """

    # User didn't write original article and user isn't trying to remove from
    # their own branch
    if name != article.author_name and article.branch != name:
        app.logger.error('Cannot delete article user does not own path: %s, author: %s deleter: %s',
                         article.full_path, article.author_name, name)
        return False

    # First remove from cache even if removing the actual file fails this will
    # be OK b/c we'll just end up re-caching it.
    cache.delete_article(article)

    # We don't save meta data for branches so either remove meta data file or
    # update original articles meta data to remove the branch link.
    if article.branch == 'master':
        # Remove the meta data file next since that's the most important for
        # us finding an article from the API.
        meta_data_file = meta_data_path_for_article_path(article.full_path)

        if not remote.remove_file_from_github(meta_data_file, message, name,
                                              email, article.branch):
            return False
    else:
        if not save_branched_article_meta_data(article, name, email,
                                               add_branch=False):
            return False

    if not remote.remove_file_from_github(article.full_path, message,
                                          name, email, article.branch):
        return False

    # FIXME: Need to update the cache reference to the original article so we
    # don't think this branch still exists in cache.

    return True


def parse_full_path(path):
    """
    Parse full path and return tuple of details embedded in path

    :param path: Full path to file including repo and owner
    :returns: path_details tuple
    """

    tokens = path.split('/')

    # Repo path is user/repo_name
    repo_path = '/'.join(tokens[:2])
    filename = tokens[-1]

    return path_details(repo_path, filename)


class Article(object):
    """
    Object representing article
    """

    def __init__(self, title, author_name, filename=ARTICLE_FILENAME,
                 repo_path=None, branch='master', stacks=None, sha=None,
                 content=None, external_url=None, image_url=None,
                 author_real_name=None):
        """
        Initalize article object

        :param title: Title of article
        :param author_name: Name of original author
        :param filename: Name of file to save article in
        :param repo_path: Path to repository to save article in
        :param branch: Branch to save article to
        :param stacks: Language/stack article primarily covers
        :param sha: Git SHA of article (if article already exists in repo)
        :param content: Contents of article
        :param external_url: External URL to view article at
        :param image_url: URL to image to show for article
        :param author_real_name: Optional real name of author, not username
        """

        self.title = title
        self.author_name = author_name
        self.stacks = stacks or []
        self.content = content
        self.external_url = external_url
        self.filename = filename
        self.image_url = image_url
        self.last_updated = None
        self.author_real_name = author_real_name

        # Only useful if article has already been saved to github
        self.sha = sha

        self.repo_path = repo_path
        if self.repo_path is None:
            self.repo_path = main_article_path()

        # Branch this article is on
        self.branch = branch

        # List of branch names where this article also exists
        self.branches = []

        self.path = '%s' % (utils.slugify(self.title))
        self.published = False

    def __repr__(self):
        return '<author_name: %s title: %s published: %s>' % (self.author_name,
                                                              self.title,
                                                              self.published)

    @staticmethod
    def from_json(str_):
        """
        Create article object from json string

        :param str_: json string representing article
        :returns: Article object
        """

        dict_ = json.loads(str_)

        # Required arguments
        title = dict_.pop('title', None)
        author_name = dict_.pop('author_name', None)

        article = Article(title, author_name)
        for attr, value in dict_.iteritems():
            setattr(article, attr, value)

        return article

    @property
    def full_path(self):
        """
        Get full path to article including repo information
        :returns:  Full path to article
        """
        return '%s/%s/%s' % (self.repo_path, self.path, self.filename)
