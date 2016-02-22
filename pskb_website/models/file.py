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
from .. import cache
from ..forms import STACK_OPTIONS


PUB_FILENAME = u'published.md'
UNPUB_FILENAME = u'unpublished.md'

# Add author's image url here

# Parse a line of markdown into 2 links and list of stacks
TITLE_RE = re.compile(r'###\s+(?P<title>.*)\s+by\s+(?P<author_real_name>.*)')
URL_RE = re.compile(r'.*?\[(?P<text>.*?)\]\((?P<url>.*?)\).*?')
IMG_RE = re.compile(r'.*\<img src="(.*?)" .*')

# The list of stacks has all sorts of special characters and commas in it so
# parsing it requires a regex with everything escaped.
STACK_RE = re.compile('|'.join(re.escape(s) for s in STACK_OPTIONS))

file_listing_item = collections.namedtuple('file_listing_item',
                                ['title', 'url', 'author_name',
                                 'author_real_name', 'author_img_url',
                                 'thumbnail_url', 'stacks'])


def read_file(path, rendered_text=True, branch=u'master'):
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


def published_articles(branch=u'master'):
    """
    Get iterator through list of published articles from file listing

    :param branch: Name of branch to save file listing to
    :returns: Generator to iterate through file_listing_item tuples
    """

    return _read_file_listing(PUB_FILENAME, branch=branch)


def unpublished_articles(branch=u'master'):
    """
    Get iterator through list of unpublished articles from file listing

    :param branch: Name of branch to save file listing to
    :returns: Generator to iterate through file_listing_item tuples
    """

    return _read_file_listing(UNPUB_FILENAME, branch=branch)


def update_article_listing(article_url, title, author_url, author_name,
                           committer_name, committer_email,
                           author_img_url=None, thumbnail_url=None,
                           stacks=None, branch=u'master', published=False):
    """
    Update article file listing with given article info

    :param article_url: URL to article
    :param title: Title of article to put in listing
    :param author_url: URL to author
    :param author_name: Name of author (i.e. login/username)
    :param committer_name: Name of user committing change
    :param committer_email: Email of user committing change
    :param author_img_url: Optional URL to author's image
    :param thumbnail_url: Optional URL to thumbnail image for article
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

    text = get_updated_file_listing_text(start_text,
                                         article_url,
                                         title,
                                         author_url,
                                         author_name,
                                         author_img_url,
                                         thumbnail_url,
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
                                committer_email, branch=u'master'):
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
                      branch=u'master'):
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
                                             article.image_url,
                                             article.thumbnail_url,
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


def _read_file_listing(path_to_listing, branch=u'master'):
    """
    Get iterator through list of published or unpublished articles

    :param path_to_listing: Path to file containing file listing
    :param branch: Name of branch to save file listing to
    :returns: Generator to iterate through file_listing_item tuples
    """

    text = cache.read_article(path_to_listing, branch)
    if text is None:
        details = read_file(path_to_listing, rendered_text=False, branch=branch)
        if details is None:
            raise StopIteration

        text = details.text
        cache.save_article(path_to_listing, branch, text, timeout=60 * 10)

    for item in _read_items_from_file_listing(text):
        yield item


def _iter_article_sections_from_file_listing(text):
    """
    Generator through raw lines file listing broken up by article

    :param text: Raw text as read from file listing file
    :returns: Generator to iterate through chunks of lines
    """

    lines_for_article = []
    for line in text.splitlines():
        line = line.strip()

        # Start of new article
        if line.startswith('### ') and lines_for_article:
            yield lines_for_article

            lines_for_article = [line]
        elif line:
            lines_for_article.append(line)

    # Don't forget last section that won't have an ending delimeter
    if lines_for_article:
        yield lines_for_article


def _read_items_from_file_listing(text):
    """
    Generator to yield parsed file_listing_item from text

    :param text: Raw text as read from file listing file
    :returns: Generator to iterate through file_listing_item tuples
    """

    for lines in _iter_article_sections_from_file_listing(text):
        try:
            item = _parse_file_listing_lines(lines)
        except ValueError as err:
            app.logger.error('Failed parsing file listing lines: %s (%s)',
                             lines, err)
        else:
            yield item


def _parse_file_listing_lines(lines):
    """
    Parse list of lines from file listing

    :param lines: Lines of text from file listing markdown file
    :returns: file_listing_item tuple or None if parsing failed
    """

    if len(lines) < 3:
        raise ValueError('At least 3 lines of required information')

    # First line
    title, author_real_name = _parse_title_line(lines[0])
    if title is None or author_real_name is None:
        raise ValueError('Title must be on first line')

    # Second line
    _, article_url = _parse_url_line(lines[1])
    if article_url is None:
        raise ValueError('Link to article must be on second line')

    # Third line
    author_name, author_img_url = _parse_author_info_line(lines[2])
    if author_name is None:
        raise ValueError('Missing author name on third line')

    # Optional 4th line of stacks
    stacks = []
    if len(lines) >= 4:
        stacks = _parse_stacks_line(lines[3])

    # Optional 5th (or 4th line) of thumbnail
    thumbnail_url = None

    # No stacks but still have thumbnail
    if not stacks and len(lines) >= 4:
        _, thumbnail_url = _parse_url_line(lines[3])
    elif len(lines) >= 5:
        _, thumbnail_url = _parse_url_line(lines[4])

    return file_listing_item(title, article_url, author_name, author_real_name,
                             author_img_url, thumbnail_url, stacks)


def _parse_title_line(line):
    """
    Parse title line of text

    :param line: Line of text to parse
    :returns: Tuple of (title, author name) or (None, None) if no match on line
    """

    match = TITLE_RE.match(line)
    if not match:
        return (None, None)

    title = _force_unicode(match.group('title'))
    author_real_name = _force_unicode(match.group('author_real_name'))

    return (title, author_real_name)


def _parse_url_line(line):
    """
    Parse URL from line of text

    :param line: Line of text to parse
    :returns: Tuple of (text, URL) or (None, None) if no match is found on line
    """

    match = URL_RE.match(line)
    if match is None:
        return (None, None)

    return (_force_unicode(match.group('text')),
            _force_unicode(match.group('url')))


def _parse_author_info_line(line):
    """
    Parse author name and optional image url from line

    :param line: Line of text to parse
    :returns: Tuple of (author_name, image_url) image_url can be None
    """

    author_name = None
    match = URL_RE.match(line)
    if match is not None:
        author_name = _force_unicode(match.group('url').split('/')[-1])

    author_img_url = None
    match = IMG_RE.match(line)
    if match is not None:
        author_img_url = _force_unicode(match.group(1))

    return (author_name, author_img_url)


def _parse_stacks_line(line):
    """
    Parse list of stacks from line of text

    :param line: Line of text to parse
    :returns: List of stacks
    """

    return [_force_unicode(m.group()) for m in STACK_RE.finditer(line)]


def _force_unicode(text):
    """
    Force text to utf-8 unicode

    :param text: Text to convert
    :returns: Unicode string
    """

    try:
        return unicode(text, encoding='utf-8')
    except TypeError:
        return text


def _file_listing_to_markdown(article_url, title, author_url, author_name,
                              author_img_url=None, thumbnail_url=None,
                              stacks=None):
    """
    Encode details in a line of markdown for the file listing file

    :param article_url: URL to article
    :param title: Title of article to put in listing
    :param author_url: URL to author
    :param author_name: Name of author to use for author link
    :param author_img_url: Optional URL to image for author
    :param thumbnail_url: Optional URL to thumbnail image for article
    :param stacks: Optional list of stacks article belongs to
    :returns: String of markdown text
    """

    title_line = u'### {title} by {author_name}'.format(
                                                    title=title,
                                                    author_name=author_name)

    article_link_line = u'- [Read the guide]({article_url})'.format(
                                                    article_url=article_url)

    author_line = u'- [Read more from {author_name}]({author_url})'.format(
                                                    author_name=author_name,
                                                    author_url=author_url)
    if author_img_url is not None:
        # Github used to support specifying the image in markdown but that
        # doesn't seem to work anymore.
        author_line = u'{author_line} <img src="{author_img_url}" width="{width}" height="{height}" alt="{author_name}" />'.format(
                                                author_line=author_line,
                                                author_name=author_name,
                                                author_img_url=author_img_url,
                                                width=30,
                                                height=30)

    lines = [title_line, article_link_line, author_line]

    if stacks:
        lines.append(u'- Related to: %s' % (','.join(stacks)))

    if thumbnail_url is not None:
        # This is purposely NOT an image link b/c we don't want to clutter up
        # the github view of this file with big images.
        lines.append(u'- [Thumbnail](%s)' % (thumbnail_url))

    lines.append(u'\n')

    return u'\n'.join(lines)


def get_updated_file_listing_text(text, article_url, title, author_url,
                                  author_name, author_img_url=None,
                                  thumbnail_url=None, stacks=None):
    """
    Update text for new article listing

    :param text: Text of file listing file
    :param article_url: URL to article
    :param title: Title of article to put in listing
    :param author_url: URL to author
    :param author_name: Name of author (i.e. login/username)
    :param author_img_url: Optional URL to image for author
    :param thumbnail_url: Optional URL to thumbnail image for article
    :param stacks: Optional list of stacks article belongs to
    :returns: String of text with article information updated
    """

    new_contents = []
    changed_section = False

    for lines in _iter_article_sections_from_file_listing(text):
        # Already found the line we need to replace so just copy remainder of
        # text to new contents and we'll write it out.
        if changed_section:
            new_contents.append(u'\n' + u'\n'.join(lines))
            continue

        try:
            item = _parse_file_listing_lines(lines)
        except ValueError as err:
            app.logger.error('Failed parsing article section: %s (%s)',
                             lines, err)
            item = None

        if item is not None and item.title == title:
            changed_section = True

            new_text = _file_listing_to_markdown(article_url, title,
                                                 author_url, author_name,
                                                 author_img_url, thumbnail_url,
                                                 stacks)

            new_contents.append(u'\n' + new_text)
        else:
            new_contents.append(u'\n' + u'\n'.join(lines))

    # Must be a new article section
    if not changed_section:
        new_text = _file_listing_to_markdown(article_url, title, author_url,
                                             author_name, author_img_url,
                                             thumbnail_url, stacks)
        new_contents.append(u'\n' + new_text)

    return u'\n'.join(new_contents)


def get_removed_file_listing_text(text, title):
    """
    Remove given title from file listing text and return result

    :param text: Text of file listing file
    :returns: String of text with title removed
    """

    new_lines = []

    for lines in _iter_article_sections_from_file_listing(text):
        try:
            item = _parse_file_listing_lines(lines)
        except ValueError as err:
            app.logger.error('Failed parsing article section: %s (%s)',
                             lines, err)
            item = None

        if item is not None and item.title == title:
            continue

        new_lines.extend(lines)

    return u'\n'.join(new_lines)
