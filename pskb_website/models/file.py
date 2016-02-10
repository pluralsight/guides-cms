"""
More direct wrapper around reading files from remote storage

This module serves as a small abstraction away from the remote storage so it
can easily be switched if needed while keeping the API the same.
"""

import collections
import re

from .. import app
from .. import remote
from .. import filters


PUB_FILENAME = 'published.md'
UNPUB_FILENAME = 'unpublished.md'

# Parse a line of markdown into 2 links and list of stacks
MD_LINE = re.compile(r'\-*\s*\[(?P<title>.*?)\]\((?P<title_url>.*?)\).*\[(?P<author_real_name>.*?)\]\((?P<author_url>.*?)\)\s+(?P<stacks>.*)')


file_listing_item = collections.namedtuple('file_listing_item',
                                'title, author_name, author_real_name, stacks')


def read_file(path, rendered_text=True, branch='master'):
    """
    Read file

    :param path: Short path to file, not including repo or owner
    :param branch: Name of branch to read file from
    :returns: remote.file_details tuple or None if file is missing
    """

    full_path = '%s/%s' % (remote.default_repo_path(), path)
    return remote.read_file_from_github(full_path, branch, rendered_text)


def published_article_path():
    """
    Get path to published article file listing

    :returns: Path to published article file listing file
    """

    return '%s/%s' % (remote.default_repo_path(), PUB_FILENAME)


def unpublished_article_path():
    """
    Get path to unpublished article file listing

    :returns: Path to unpublished article file listing file
    """

    return '%s/%s' % (remote.default_repo_path(), UNPUB_FILENAME)


def published_articles(branch='master'):
    """
    Get iterator through list of published articles from file listing

    :param branch: Name of branch to save file listing to
    :returns: Generator to iterate through file_listing_item tuples
    """

    return _read_file_listing(PUB_FILENAME, branch=branch)


def unpublished_articles(branch='master'):
    """
    Get iterator through list of unpublished articles from file listing

    :param branch: Name of branch to save file listing to
    :returns: Generator to iterate through file_listing_item tuples
    """

    return _read_file_listing(UNPUB_FILENAME, branch=branch)


def update_article_listing(article_url, title, author_url, author_name,
                           committer_name, committer_email, stacks=None,
                           branch='master', published=False):
    """
    Update article file listing with given article info

    :param article_url: URL to article
    :param title: Title of article to put in listing
    :param author_url: URL to author
    :param author_name: Name of author (i.e. login/username)
    :param committer_name: Name of user committing change
    :param committer_email: Email of user committing change
    :param stacks: Optional list of stacks article belongs to
    :param branch: Name of branch to save file listing to
    :param published: Boolean to update listing of published articles or list
                      of unpublished articles

                      If published is True then the artitle title is removed
                      from the unpublished listing (if it exists).

                      If published is False then the article title is removed
                      from the published listing (if it exists).

    :returns: True or False if file listing was updated
    """

    if published:
        path_to_listing = published_article_path()
        filename = PUB_FILENAME
        message = 'Adding "%s" to published articles' % (title)
    else:
        path_to_listing = unpublished_article_path()
        filename = UNPUB_FILENAME
        message = 'Adding "%s" to unpublished articles' % (title)

    sha = None
    start_text = ''
    details = read_file(filename, rendered_text=False, branch=branch)
    if details is not None:
        sha = details.sha
        start_text = details.text

    text = get_updated_file_listing_text(start_text, article_url, title,
                                         author_url, author_name,
                                         stacks=stacks)

    success = True
    if start_text != text:
        success = remote.commit_file_to_github(path_to_listing, message, text,
                                               committer_name, committer_email,
                                               sha=sha, branch=branch)
    if not success:
        return success

    # Now update the opposite file so the article is only on 1 file at a time
    published = not published

    return remove_article_from_listing(title, published, committer_name,
                                       committer_email, branch=branch)


def remove_article_from_listing(title, published, committer_name,
                                committer_email, branch='master'):
    """
    Remove article title from file listing

    :param title: Title of article to remove from listing
    :param committer_name: Name of user committing change
    :param committer_email: Email of user committing change
    :param branch: Name of branch to save file listing to
    :param published: Boolean to update listing of published articles or list
                      of unpublished articles
    :returns: True or False if file listing was updated
    """

    if published:
        path_to_listing = published_article_path()
        filename = PUB_FILENAME
        message = 'Removing "%s" from published articles' % (title)
    else:
        path_to_listing = unpublished_article_path()
        filename = UNPUB_FILENAME
        message = 'Removing "%s" from unpublished articles' % (title)

    sha = None
    start_text = ''

    details = read_file(filename, rendered_text=False, branch=branch)
    if details is not None:
        sha = details.sha
        start_text = details.text

    text = get_removed_file_listing_text(start_text, title)

    success = True
    if start_text != text:
        success = remote.commit_file_to_github(path_to_listing, message, text,
                                               committer_name, committer_email,
                                               sha=sha, branch=branch)

    return success


def sync_file_listing(all_articles, published, committer_name, committer_email,
                      branch='master'):
    """
    Synchronize file listing file with contents of repo

    :param all_articles: Iterable of article objects that should be synced to
                         listing
    :param published: True to sync published articles or False to sync
                      unpublished articles
    :param committer_name: Name of user committing change
    :param committer_email: Email of user committing change
    :param branch: Name of branch to save file listing to
    :returns: Boolean to indicate if syncing succeeded or failed

    This can be a very expensive operation because it heavily calls the remote
    API so be careful calling this for API limits and performance.  Ideally
    this should at least be run as some kind of background process.
    """

    if published:
        path_to_listing = published_article_path()
        filename = PUB_FILENAME
        message = 'Synchronizing published articles'
    else:
        path_to_listing = unpublished_article_path()
        filename = UNPUB_FILENAME
        message = 'Synchronizing unpublished articles'

    details = read_file(filename, rendered_text=False, branch=branch)

    text = ''
    sha = None

    if details is not None:
        text = details.text
        sha = details.sha

    start_text = text

    # Get listing of all the titles currently in the file so we know which ones
    # to remove and we'll try to remove them in order so the diff of the file
    # is sane.
    prev_titles = {item.title for item in _read_items_from_file_listing(text)}
    curr_titles = set()

    for article in all_articles:
        article_url = filters.url_for_article(article)
        author_url = filters.url_for_user(article.author_name)
        name = article.author_real_name or article.author_name
        curr_titles.add(article.title)

        text = get_updated_file_listing_text(text,
                                             article_url,
                                             article.title,
                                             author_url,
                                             name,
                                             article.stacks)

    titles_to_remove = prev_titles - curr_titles
    for title in titles_to_remove:
        text = get_removed_file_listing_text(text, title)

    if text != start_text:
        return remote.commit_file_to_github(path_to_listing, message, text,
                                            committer_name, committer_email,
                                            sha=sha, branch=branch)
    else:
        app.logger.debug('Listing unchanged so no commit being made')


def _read_file_listing(path_to_listing, branch='master'):
    """
    Get iterator through list of published or unpublished articles

    :param path_to_listing: Path to file containing file listing
    :param branch: Name of branch to save file listing to
    :returns: Generator to iterate through file_listing_item tuples
    """

    details = read_file(path_to_listing, rendered_text=False, branch=branch)
    if details is None:
        raise StopIteration

    for item in _read_items_from_file_listing(details.text):
        yield item


def _read_items_from_file_listing(text):
    """
    Generator to yield parsed file_listing_item from text

    :param text: Raw text as read from file listing file
    :returns: Generator to iterate through file_listing_item tuples
    """

    for line in text.splitlines():
        item = _parse_file_listing_line(line)
        if item is not None:
            yield item


def _parse_file_listing_line(line):
    """
    Parse line from file listing

    :param line: Line of text from file listing markdown file
    :returns: file_listing_item tuple or None if parsing failed
    """

    match = MD_LINE.match(line)
    if not match:
        return None

    author_name = match.group('author_url').split('/')[-1]
    stacks = match.group('stacks').split(',')

    return file_listing_item(match.group('title'), author_name,
                             match.group('author_real_name'), stacks)


def _file_listing_to_markdown(article_url, title, author_url, author_name,
                              stacks=None):
    """
    Encode details in a line of markdown for the file listing file

    :param article_url: URL to article
    :param title: Title of article to put in listing
    :param author_url: URL to author
    :param author_name: Name of author to use for author link
    :param stacks: Optional list of stacks article belongs to
    :returns: String of markdown text
    """

    if stacks is None:
        stacks = []

    return '[{title}]({article_url}) by [{author_name}]({author_url}) {stacks}'.format(
            title=title, article_url=article_url, author_name=author_name,
            author_url=author_url, stacks=','.join(stacks))


def get_updated_file_listing_text(text, article_url, title, author_url,
                                  author_name, stacks=None):
    """
    Update text for new article listing

    :param text: Text of file listing file
    :param article_url: URL to article
    :param title: Title of article to put in listing
    :param author_url: URL to author
    :param author_name: Name of author (i.e. login/username)
    :param stacks: Optional list of stacks article belongs to
    :returns: String of text with article information updated
    """

    new_contents = []
    changed_line = False

    for line in text.splitlines():
        # Already found the line we need to replace so just copy remainder of
        # text to new contents and we'll write it out.
        if changed_line:
            new_contents.append(line)
            continue

        item = _parse_file_listing_line(line)

        if item is not None and item.title == title:
            changed_line = True

            # Use '- ' to create markdown list
            line = '- ' + _file_listing_to_markdown(article_url,
                                                    title,
                                                    author_url,
                                                    author_name,
                                                    stacks=stacks)

        new_contents.append(line)

    if not changed_line:
        line = _file_listing_to_markdown(article_url, title, author_url,
                                         author_name, stacks=stacks)
        new_contents.append('- ' + line)

    return '\n'.join(new_contents)


def get_removed_file_listing_text(text, title):
    """
    Remove given title from file listing text and return result

    :param text: Text of file listing file
    :returns: String of text with title removed
    """

    new_lines = []

    for line in text.splitlines():
        item = _parse_file_listing_line(line)

        if item is not None and item.title == title:
            continue

        new_lines.append(line)

    return '\n'.join(new_lines)
