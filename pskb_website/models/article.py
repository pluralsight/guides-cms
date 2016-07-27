"""
Article related model API
"""

import collections
import itertools
import json
import subprocess
import os

from . import lib
from . import file as file_mod
from .user import find_user
from .heart import count_hearts
from .. import url_for_domain
from .. import app
from .. import PUBLISHED, IN_REVIEW, DRAFT, STATUSES
from .. import cache
from .. import remote
from .. import utils

# FIXME: This file is fairly modular to the outside world but internally it's
# very fragmented and the layers of abstraction are all mixed up.  Needs a lot
# of TLC...

FILE_EXTENSION = '.md'
ARTICLE_FILENAME = 'article%s' % (FILE_EXTENSION)
ARTICLE_METADATA_FILENAME = 'details.json'
DEFAULT_STACK = u'other'

path_details = collections.namedtuple('path_details', 'repo, filename')


def get_available_articles(status=None, repo_path=None):
    """
    Get iterator for current article objects

    :param status: PUBLISHED, IN_REVIEW, DRAFT, or None to read all articles
    :param repo_path: Optional repo path to read from (<owner>/<name>)

    :returns: Iterator through article objects

    Note that article objects only have path, title, author name, and stacks
    filled out.  You'll need to call read_article() to get full article
    details.
    """

    if status is None or repo_path is not None:
        for article in get_available_articles_from_api(status=status,
                                                       repo_path=repo_path):
            yield article

        raise StopIteration

    # Shortcuts to read listing of files from a single file read instead of
    # using the API to read every file
    if status == PUBLISHED:
        items = file_mod.published_articles()
    elif status == IN_REVIEW:
        items = file_mod.in_review_articles()
    elif status == DRAFT:
        items = file_mod.draft_articles()

    for item in items:
        article = Article(item.title, item.author_name,
                          author_real_name=item.author_real_name,
                          stacks=item.stacks)
        article.publish_status = status

        if item.thumbnail_url:
            article.thumbnail_url = item.thumbnail_url

        if item.author_img_url:
            article.image_url = item.author_img_url

        yield article


def search_for_article(title, stacks=None, status=None):
    """
    Search for an article by the title and optionally stack and status

    :param title: Title of article to search for
    :param stacks: Optional list of stacks to search All stacks are searched if
                   None is given
    :param status: Optional status to search for All possible statuses are
                   searched if None is given
    :returns: Article object if found or None if not found
    """

    statuses = [status] if status is not None else STATUSES

    if stacks is None:
        stacks = []
    else:
        # Normalize so we don't have to deal with case issues
        stacks = [s.lower() for s in stacks]

    for status in statuses:
        articles = get_available_articles(status=status)
        article = find_article_by_title(articles, title)

        if article is None:
            continue

        if not stacks:
            return article

        for requested_stack in stacks:
            for article_stack in article.stacks:
                if article_stack.lower() == requested_stack:
                    return article

    return None


def get_available_articles_from_api(status=None, repo_path=None):
    """
    Get iterator for current article objects

    :param status: PUBLISHED, IN_REVIEW, DRAFT, or None to read all articles
    :param repo_path: Optional repo path to read from (<owner>/<name>)

    :returns: Iterator through article objects

    Note that article objects only have path, title and author name filled out.
    You'll need to call read_article() to get full article details.
    """

    # Go through the minimal listing of articles and turn it into the full
    # article objects.  This way the github layer only knows what's available
    # on github and doesn't have knowledge of how we organize things, etc.
    if repo_path is None:
        repo_path = remote.default_repo_path()

        articles = cache.read_file_listing(status)
        if articles is not None:
            for article in articles_from_json(articles):
                yield article

            raise StopIteration

    files_to_cache = []

    for file_details in remote.files_from_github(repo_path, ARTICLE_FILENAME):
        # We're only caching published articles right now so don't waste a
        # roundtrip to cache if that's not what caller wants.
        article = None

        if status == PUBLISHED:
            article = _read_article_from_cache(file_details.path)

        if article is None:
            article = read_article_from_metadata(file_details)
            if article is None:
                continue

            article.filename = ARTICLE_FILENAME
            article.repo_path = repo_path

        if status is None or article.publish_status == status:
            yield article

        if status == PUBLISHED and article.publish_status == PUBLISHED:
            files_to_cache.append(lib.to_json(article))

    if files_to_cache:
        cache.save_file_listing('published', json.dumps(files_to_cache))


def articles_from_json(json_str):
    """
    Generator to iterate through list of article objects in json format

    :param json_str: JSON string
    :returns: Generator through article objects
    """

    for json_str in json.loads(json_str):
        try:
            yield Article.from_json(json_str)
        except ValueError:
            app.logger.error('Failed parsing json meta data from cache "%s"',
                             json_str)
            continue

    raise StopIteration


def get_articles_for_author(author_name, status=None):
    """
    Get iterator for articles from given author

    :param author_name: Name of author to find articles for
    :param status: PUBLISHED, IN_REVIEW, DRAFT, or None to read all articles
    :returns: Iterator through article objects
    """

    if status is None:
        articles = itertools.chain(get_available_articles(status=PUBLISHED),
                                   get_available_articles(status=IN_REVIEW),
                                   get_available_articles(status=DRAFT))
    else:
        articles = get_available_articles(status=status)

    for article in articles:
        if article.author_name == author_name:
            yield article


def get_public_articles_for_author(author_name):
    """
    Get iterator for all public i.e. non-draft articles from given author

    :param author_name: Name of author to find articles for
    :returns: Iterator through article objects
    """

    articles = itertools.chain(get_available_articles(status=PUBLISHED),
                               get_available_articles(status=IN_REVIEW))

    for article in articles:
        if article.author_name == author_name:
            yield article


def group_articles_by_status(articles):
    """
    Group articles by publish status

    :param articles: Iterable of Article objects
    :returns: Iterable like itertools.groupby with a key as the publish_status
              and a list of articles for that status
    """

    def status_key(a):
        if a.publish_status == PUBLISHED:
            cnt = 1
        elif a.publish_status == IN_REVIEW:
            cnt = 2
        elif a.publish_status == DRAFT:
            cnt = 3
        else:
            cnt = 4

        return cnt

    sorted_by_status = sorted(articles, key=status_key)

    return itertools.groupby(sorted_by_status, key=lambda a: a.publish_status)


def author_stats(statuses=None):
    """
    Get number of articles for each author

    :param statuses: List of statuses to aggregate stats for
    :param statuses: Optional status to aggregate stats for, all possible
                     statuses are counted if None is given
    :returns: Dictionary mapping author names to number of articles::

        {author_name: [article_count, avatar_url]}

    Note avatar_url can be None and is considered optional
    """

    cache_key = 'author-stats'
    stats = cache.get(cache_key)
    if stats:
        return json.loads(stats)

    stats = {}
    statuses = [get_available_articles(status=st) for st in statuses]
    for article in itertools.chain(*statuses):
        # This is ALMOST a good fit for collections.defaultdict() but we need
        # to inspect the avatar URL each time to see if it can be replaced with
        # a non-empty value since this is optional article information.
        try:
            prev_stats = stats[article.author_name]
        except KeyError:
            prev_stats = [1, None]
        else:
            prev_stats[0] += 1

            if prev_stats[1] is None and article.image_url is not None:
                prev_stats[1] = article.image_url

        stats[article.author_name] = prev_stats

    if not stats:
        return stats

    # Just fetch stats every 30 minutes, this is not a critical bit of data
    cache.save(cache_key, json.dumps(stats), timeout=30 * 60)
    return stats


def read_article(path, rendered_text=False, branch=u'master', repo_path=None,
                 allow_missing=False):
    """
    Read article

    :param path: Short path to article, not including repo or owner
    :param rendered_text: Boolean to read rendered or raw text
    :param branch: Name of branch to read file from
    :param repo_path: Optional repo path to read from (<owner>/<name>)
    :param allow_missing: False to log warning for missing or True to allow it
                          i.e.  when you're just seeing if an article exists

    :returns: Article object
    """

    if repo_path is None:
        repo_path = remote.default_repo_path()

    full_path = '%s/%s' % (repo_path, path)

    # Handle scenario where caller forgets to include filename, default it
    if not path.endswith(FILE_EXTENSION):
        slash = '' if path.endswith('/') else '/'
        full_path = '%s%s%s' % (full_path, slash, ARTICLE_FILENAME)

    article = _read_article_from_cache(path, branch)
    if article is not None:
        return article

    details = remote.read_file_from_github(full_path, branch, rendered_text,
                                           allow_404=allow_missing)

    # Allow empty sha when requesting rendered_text b/c of the way the
    # underlying remote API works. See read_file_from_github for more
    # information.
    if details is None or details.text is None or (details.sha is None and not rendered_text):
        if not allow_missing:
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
        # high-traffic data like the rendered view of the articles.
        if rendered_text:
            # Force read of contributors and only cache it for published
            # guides. Again, trying to save on cache space, and we're not too
            # concerned with the list of contributors until a guide is
            # published.
            if article.published:
                article._read_contributors_from_api(remove_ignored_users=True)

            cache.save_file(article.path, article.branch, lib.to_json(article))
    else:
        # We cannot properly show an article without metadata.
        article = None
        app.logger.error('Failed reading meta data for %s, full_path: %s, branch: %s',
                         path_info, full_path, branch)

    if article is not None and article.image_url is None:
        user = find_user(article.author_name)
        if user is not None:
            article.image_url = user.avatar_url

    return article


def read_article_from_metadata(file_details):
    """
    Read article object from json metadata

    :param file_details: remote.file_details object
    :returns: Article object with metadata filled out or None

    Note the article contents are NOT filled out here!
    """

    path_info = parse_full_path(file_details.path)
    json_str = read_meta_data_for_article_path(file_details.path)
    if json_str is None:
        # Cannot do anything here b/c we do not know the title.
        app.logger.error('Failed reading meta data for "%s", file_details: %s',
                         path_info, file_details)
        return None

    try:
        return Article.from_json(json_str)
    except ValueError:
        app.logger.error('Failed parsing json meta data for "%s", file_details: %s, json: %s',
                         path_info, file_details, json_str)
        return None


def save_article(title, message, new_content, author_name, email, sha,
                 branch=u'master', image_url=None, repo_path=None,
                 author_real_name=None, stacks=None, status=DRAFT,
                 first_commit=None):
    """
    Create or save new (original) article, not branched article

    :param title: Title of article
    :param message: Commit message to save article with
    :param content: Content of article
    :param author_name: Name of author who wrote article
    :param email: Email address of author
    :param sha: Optional SHA of article if it already exists on github (This
                must be the SHA of the current version of the article that is
                being replaced.)
    :param branch: Name of branch to commit file to (branch must already
                   exist)
    :param image_url: Image to use for article
    :param repo_path: Optional repo path to save into (<owner>/<name>)
    :param author_real_name: Optional real name of author, not username
    :param stacks: Optional list of stacks to associate with article
    :param status: PUBLISHED, IN_REVIEW, or DRAFT
    :param first_commit: Optional first commit of article if it already exists

    :returns: Article object updated or saved or None for failure

    This function is not suitable for saving branched articles.  The article
    created here will be attributed to the given author_name whereas branched
    articles should be created with branch_article() so the correct author
    information is maintained.
    """

    article = Article(title, author_name, branch=branch, image_url=image_url,
                      repo_path=repo_path, author_real_name=author_real_name,
                      stacks=stacks)
    article.publish_status = status
    article.first_commit = first_commit
    article.content = new_content

    commit_sha = remote.commit_file_to_github(article.full_path, message,
                                              new_content, author_name, email,
                                              sha, branch)
    if commit_sha is None:
        return commit_sha

    # Had no previous SHA so this must be the first time we're saving it
    if not sha:
        article.first_commit = commit_sha

    if branch != u'master':
        commit_sha = save_branched_article_meta_data(article, author_name, email)
    else:
        commit_sha = save_article_meta_data(article, author_name, email, branch)

    if commit_sha is None:
        # FIXME: Handle error. This is interesting b/c now we created the
        # article, but not the meta data.
        return commit_sha

    _delete_article_from_cache(article)
    return article


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

    New branch will be named after author of changes and title
    """

    branch = '%s-%s-%s' % (author_name, utils.slugify_stack(article.stacks[0]),
                           utils.slugify(article.title))

    article_sha = article.sha

    # Create branch if we needed to
    repo_sha = remote.read_branch(article.repo_path, branch)
    if repo_sha is None:
        repo_sha = remote.read_branch(article.repo_path, u'master')
        if repo_sha is None:
            app.logger.error('Cannot find master branch "%s"',
                             article.repo_path)
            return None

        if not remote.create_branch(article.repo_path, branch, repo_sha):
            return None

    # Branch already exists
    else:
        # To make diffs look correct and history to be maintained between
        # branches we take into account the situation here where the branch
        # already existed but the article we're branching is not in the branch
        # yet.  In this case we want to merge the commits for this article into
        # the branch. Then, any changes this branch is introducing will show up
        # clearly in the diff instead of just adding this article to the branch
        # as a new file.
        if not remote.merge_branch(article.repo_path, branch, u'master',
                                   'Merging recent changes from master'):
            # This isn't ideal but if the merge fails we still allow the user
            # to make their branched article.  The diff/history will be a bit
            # weird but we'd have to manually do the merge so it's not feasible
            # via the API.
            app.logger.warning('Failed merging branches so commiting branched article as new/updated file to branch')

        # Try to read this article from the branch to update the SHA.
        # This ensures we have the most up-to-date SHA for the file we're
        # modifying, which is required by github API. For example, this article
        # might already exist on the branch but the article.sha is the SHA for
        # the ORIGINAL article, not branch.
        branch_file = remote.file_details_from_github(article.full_path,
                                                      branch=branch)
        if branch_file is not None:
            article_sha = branch_file.sha

    return save_article(article.title, message, new_content, author_name,
                        email, article_sha, branch=branch, image_url=image_url,
                        author_real_name=author_real_name,
                        stacks=article.stacks, status=article.publish_status)


def branch_or_save_article(title, path, message, content, author_name, email,
                           sha, image_url, repo_path=None,
                           author_real_name=None, stacks=None,
                           first_commit=None):
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
    :param first_commit: SHA of first commit to save with article

    :returns: Article object updated, saved, or branched
    """

    article = None
    status = DRAFT

    if path:
        article = read_article(path, rendered_text=False, branch=u'master',
                               repo_path=repo_path)
        if article is None:
            app.logger.error('Failed reading article from %s to update', path)
            return None

        status = article.publish_status
        first_commit = article.first_commit

    if article and article.author_name != author_name and sha:
        # Note branching an article cannot change the stacks!
        new = branch_article(article, message, content, author_name, email,
                             image_url, author_real_name=author_real_name)
    else:
        new = save_article(title, message, content, author_name, email,
                           sha, image_url=image_url, repo_path=repo_path,
                           author_real_name=author_real_name,
                           stacks=stacks, status=status,
                           first_commit=first_commit)

    return new


def save_article_meta_data(article, author_name=None, email=None, branch=None,
                           update_branches=True):
    """
    :param article: Article object
    :param author_name: Name of author who wrote article (optional)
    :param email: Email address of author (optional)
    :param branch: Optional branch to save metadata, if not given
                   article.branch will be used
    :param update_branches: Optional boolean to update the metadata branches of
                            the article with the given branch (True) or to save
                            article branches as-is (False)
    :returns: SHA of commit or None if commit failed

    Note that author_name and email can be None if the site 'admin' is changing
    the meta data.  However, author_name and email must both exist or both be
    None.
    """

    filename = meta_data_path_for_article_path(article.full_path)

    if branch is None:
        branch = article.branch

    # Get sha of meta data if it exists so we can update it if it already
    # exists
    details = remote.read_file_from_github(filename, rendered_text=False,
                                           branch=branch, allow_404=True)
    sha = None
    text = None
    if details is not None:
        sha = details.sha
        text = details.text

        orig_article = Article.from_json(details.text)

        if update_branches:
            # Merge the original article metadata with the new version.
            # Currently the only thing that can change here is the list of
            # branches. We only modify the list of branches when saving a
            # branched article so we merge the two lists of branches here since
            # removal of a branch should happen elsewhere.
            for orig_branch in orig_article.branches:
                if orig_branch not in article.branches:
                    article.branches.append(orig_branch)

    # Don't need to serialize everything, just the important stuff that's not
    # stored in the path and article.
    exclude_attrs = ('content', 'external_url', 'sha', 'repo_path', '_path',
                     'last_updated', '_contributors', '_heart_count')
    json_content = lib.to_json(article, exclude_attrs=exclude_attrs)

    # Nothing changed so no commit needed
    if text is not None and json_content == text:
        return True

    message = u'Updating article metadata for "%s"' % (article.title)

    _delete_article_from_cache(article)

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
    :returns: SHA of commit or None if commit failed

    Metadata for branched articles should be identical to the original article.
    This makes it easier for automatically merging changes because metadata
    differences won't get in the way.  The author_name is the only thing useful
    for a branched article.  However, that should already be encoded in the
    branch name and the commits.  So, editors of original articles will get
    credit for helping via those mechanisms, not metadata.
    """

    orig_article = read_article(article.path, rendered_text=False,
                                branch=u'master', repo_path=article.repo_path)

    # Save list of author name and branch name. Yes, we could parse the name
    # out of the branch but that is tricky b/c we'd have to disallow some
    # characters in the author name to parse properly.
    # Technically this would be better suited as a tuple but we serialize the
    # data as json, which doesn't support tuples. Serializing tuples to json
    # just comes back as a list anyway.
    branch_info = [author_name, article.branch]

    # Nothing to save, we're already tracking this branch
    if add_branch:
        if branch_info in orig_article.branches:
            return True

        orig_article.branches.append(branch_info)
    else:
        try:
            orig_article.branches.remove(branch_info)
        except ValueError:
            # Branch isn't being tracked anyway so nothing to remove
            return True

    # Note we don't ever change metadata on the branches. This keeps the
    # metadata from showing in up in merges. We only want to deal with article
    # text for merges.
    return save_article_meta_data(orig_article, author_name, email,
                                  update_branches=False)


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
    _delete_article_from_cache(article)

    # We don't save meta data for branches so either remove meta data file or
    # update original articles meta data to remove the branch link.
    if article.branch == u'master':
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


def find_article_by_title(articles, title):
    """
    Search through list of article objects looking for article with given title

    :param articles: List of article objects
    :param title: Title to search for
    :returns: article object or None if not found
    """

    title = utils.slugify(title)

    for article in articles:
        if utils.slugify(article.title) == title:
            return article

    return None


def change_article_stack(orig_path, orig_stack, new_stack, title, author_name,
                         email):
    """
    Change article stack

    :param orig_path: Current path to article without repo or owner
    :param orig_stack: Original stack
    :param new_stack: New stack
    :param author_name: Name of author who wrote article
    :param email: Email address of author
    :returns: New path of article or None if error

    Note this function only makes changes to articles on the master branch!
    """

    # Ugly circular imports
    from .. import tasks

    new_path = orig_path.replace(utils.slugify_stack(orig_stack),
                                 utils.slugify_stack(new_stack))
    try:
        tasks.move_article(orig_path, new_path, title, author_name, email)
    except subprocess.CalledProcessError as err:
        app.logger.error(err)
        return None

    cache.delete_file(orig_path, u'master')

    return new_path


def delete_branch(article, branch_to_delete):
    """
    Delete branch of guide and save to github

    :param article: Article object to delete branch from
    :param branch_to_delete: Branch of guide to delete
    :returns: True if deleted or False otherwise
    """

    for author, branch_name in article.branches:
        if branch_name == branch_to_delete:
            article.branches.remove([author, branch_name])
            break
    else:
        app.logger.error('Unable to find branch to delete branch: "%s", stack: "%s", title:"%s"',
                         branch_to_delete, article.stacks[0], article.title)
        return False

    # Note we don't use a author name or email here b/c we're committing this
    # as the REPO_OWNER. We don't have access to that email address unless the
    # REPO_OWNER happens to be cached and/or logged in recently. So, we're not
    # even going to try.
    commit_sha = save_article_meta_data(article, branch=u'master',
                                        update_branches=False)
    if commit_sha is None:
        app.logger.error('Failed saving metadata for delete event branch: "%s", stack: "%s", title:"%s"',
                         branch_to_delete, article.stacks[0], article.title)
        return False

    _delete_article_from_cache(article)

    return True


def _delete_article_from_cache(article):
    """
    Delete given article from cache if it exists

    :param article: Article object to delete

    Note this function is harmless if the article does not exist in the cache.
    """

    # The point of this function is so outside article.py there is no knowledge
    # of what the cache key is or how we cache it.
    cache.delete_file(article.path, article.branch)

    for author, branch_name in article.branches:
        cache.delete_file(article.path, branch_name)


def _read_article_from_cache(path, branch=u'master'):
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

    json_str = cache.read_file(path, branch)
    if json_str is None:
        return None

    return Article.from_json(json_str)


class Article(object):
    """
    Object representing article
    """

    def __init__(self, title, author_name, filename=ARTICLE_FILENAME,
                 repo_path=None, branch=u'master', stacks=None, sha=None,
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
        self.stacks = stacks or [DEFAULT_STACK]
        self.content = content
        self.external_url = external_url
        self.filename = filename
        self.image_url = image_url
        self.last_updated = None
        self.thumbnail_url = None
        self.author_real_name = author_real_name or author_name
        self.first_commit = None
        self._heart_count = None

        # Only useful if article has already been saved to github
        self.sha = sha

        self.repo_path = repo_path
        if self.repo_path is None:
            self.repo_path = remote.default_repo_path()

        # Branch this article is on
        self.branch = branch

        # List of lists [author_name, branch_name] where author_name is the
        # name of the user who created the branch.  Again, would be better
        # suited as a list of tuples but we're using JSON for serialization and
        # tuples turn into lists anyway.
        self.branches = []

        self._path = None
        self._publish_status = DRAFT

        # List of User objects representing any 'author' i.e user who has
        # contributed at least 1 line of text to this article.
        self._contributors = None

    @property
    def path(self):
        return u'%s/%s/%s' % (self.publish_status,
                              utils.slugify_stack(self.stacks[0]),
                              utils.slugify(self.title))

    def __repr__(self):
        return '<author_name: %s title: %s status: %s>' % (self.author_name,
                                                           self.title,
                                                           self.publish_status)

    @property
    def stack_image_url(self):
        """
        Get path to static image for article based on stack

        None will be returned for articles without a stack image

        A full path including the domain is included in the URL so this
        property is suitable for using where places require a full link such as
        FB open graph meta tags.
        """

        for stack in self.stacks:
            file_path = os.path.join('img', 'stack_images', '%s.png' % (
                                     utils.slugify_stack(stack)))
            static_path = os.path.join(app.static_folder, file_path)

            if os.path.isfile(static_path):
                # Using _external=True even though it's redundant for our
                # wrapper unless DOMAIN is set.
                return url_for_domain('static', filename=file_path,
                                      base_url=app.config['DOMAIN'],
                                      _external=True)

        return None

    @property
    def publish_status(self):
        return self._publish_status

    @publish_status.setter
    def publish_status(self, new_status):
        if new_status not in STATUSES:
            raise ValueError('publish_status must be one of %s' % (STATUSES,))

        # Lets go ahead and delete it b/c cached publish status would be out of
        # date now
        _delete_article_from_cache(self)

        self._publish_status = new_status

    @property
    def heart_count(self):
        """
        Read number of hearts for article

        :returns: Number of hearts
        """

        if self._heart_count is not None:
            return self._heart_count

        self._heart_count = count_hearts(self.stacks[0], self.title)
        return self._heart_count

    @property
    def published(self):
        return self.publish_status == PUBLISHED

    @property
    def contributors(self):
        """
        List of tuples representing any 'author' i.e user who has contributed
        at least 1 line of text to this article.  Each tuple is in the form of
        (name, login) where name can be None.

        We use plain tuples instead of named tuples or User objects so we can
        easily seralize the contributors to JSON.

        NOTE: This property automatically removes users set to ignore via the
        contributors_to_ignore() function!  To get the full list use
        _read_contributors_from_api(remove_ignored_users=False).
        """

        # Small form of caching. This way we only fetch the contributors once.

        # NOTE: This could result in some data out of data if we have new
        # contributors after this is called but contributor information isn't
        # super important so should be ok.
        if self._contributors is not None:
            return self._contributors

        self._read_contributors_from_api(remove_ignored_users=True)

        return self._contributors

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

            # Backwards-compatability, this field was renamed
            if attr == 'published':
                attr = '_publish_status'

                if value:
                    value = PUBLISHED
                else:
                    value = DRAFT

            # Another rename so we could use a property
            elif attr == 'publish_status':
                attr = '_publish_status'

            # This field used to be optional
            elif attr == 'stacks' and not value:
                value = [DEFAULT_STACK]

            # Backwards compatability. We used to only store a list of branch
            # names b/c branches were named after editor. Now branches are
            # named after editor and article so storing this as list to track
            # who the editor is.
            elif attr == 'branches':
                branches = []

                for branch in value:
                    if isinstance(branch, (list, tuple)):
                        branches.append(branch)
                    else:
                        branches.append([branch, branch])

                value = branches

            if attr == '_publish_status' and value not in STATUSES:
                raise ValueError('publish_status must be one of %s' % (STATUSES,))

            setattr(article, attr, value)

        return article

    @property
    def full_path(self):
        """
        Get full path to article including repo information
        :returns:  Full path to article
        """
        return '%s/%s/%s' % (self.repo_path, self.path, self.filename)

    def _remove_ignored_contributors(self):
        """
        Remove ignored contributors from self._contributors according to
        contributors returned by contributors_to_ignore
        """

        ignore_names = lib.contributors_to_ignore()

        # Make a copy to loop over and remove from real list
        for user in list(self._contributors):
            if user[0] in ignore_names or user[1] in ignore_names:
                self._contributors.remove(user)

    def _read_contributors_from_api(self, remove_ignored_users=True):
        """Force reset of contributors for article and fetch from github API"""

        self._contributors = []

        # Keep track of all the logins that have names so we can only store
        # users with their full names if available.  Some contributions maybe
        # returned from the API with a full name and without a full name, just
        # depends on how the commit was done.
        logins_with_names = set()

        # We have to request the contributors for published and in-review
        # statuses if the article is published. This is a quirk to how the
        # github commit API works.  The API doesn't use git --follow so since
        # guides are moved from in-review to published we have to find any
        # authors at both locations.
        # We don't bother with requesting 'draft' status b/c we're assuming
        # only authors work on the guide in that phase.

        # Use set to track uniques but we'll turn it into a list at the end so
        # we can make sure we use a serializable type.
        unique_contributors = set()

        statuses = (PUBLISHED, IN_REVIEW)

        # No point in checking published if guide isn't published yet; saves us
        # an API request.  This could cause an issue if a guide is published,
        # gets some edits, then is unpublished.  However that doesn't happen in
        # practice so going with slight request optimization.
        if not self.published:
            statuses = (IN_REVIEW, )

        for status in statuses:
            path = u'%s/%s/%s/%s' % (status,
                                     utils.slugify_stack(self.stacks[0]),
                                     utils.slugify(self.title),
                                     self.filename)

            contribs = remote.file_contributors(path, branch=self.branch)

            # remote call returns committers as well but we're only interested
            # in authors
            for user in contribs['authors']:
                if user[1] != self.author_name:
                    if user[0] is not None:
                        logins_with_names.add(user[1])

                    unique_contributors.add(user)

        # Remove any duplicates that have empty names
        for user in unique_contributors:
            if user[0] is not None or user[1] not in logins_with_names:
                self._contributors.append(user)

        if remove_ignored_users:
            self._remove_ignored_contributors()
