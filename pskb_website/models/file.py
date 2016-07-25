"""
More direct wrapper around reading files from remote storage

This module serves as a way to read and parse common markdown file 'types' from
the repository such as the file listings for published articles, etc.
"""

import collections
import re
import json

from .. import PUBLISHED, IN_REVIEW, DRAFT
from .. import app
from .. import remote
from .. import filters
from .. import cache
from ..forms import STACK_OPTIONS


FAQ_FILENAME = u'faq.md'
CONTEST_FILENAME = u'author_contest.md'

PUB_FILENAME = u'published.md'
IN_REVIEW_FILENAME = u'in_review.md'
DRAFT_FILENAME = u'draft.md'

REDIRECT_FILENAME = u'redirects.md'

MARKDOWN_FILES = (FAQ_FILENAME, PUB_FILENAME, IN_REVIEW_FILENAME,
                  DRAFT_FILENAME, REDIRECT_FILENAME, CONTEST_FILENAME)

# Parse a line of markdown into 2 links and list of stacks
TITLE_RE = re.compile(r'###\s+(?P<title>.*)\s+by\s+(?P<author_real_name>.*)')
URL_RE = re.compile(r'.*?\[(?P<text>.*?)\]\((?P<url>.*?)\).*?')
IMG_RE = re.compile(r'.*\<img src="(.*?)" .*')

# The list of stacks has all sorts of special characters and commas in it so
# parsing it requires a regex with everything escaped.
STACK_RE = re.compile('|'.join(re.escape(s.lower()) for s in STACK_OPTIONS))

file_listing_item = collections.namedtuple('file_listing_item',
                                ['title', 'url', 'author_name',
                                 'author_real_name', 'author_img_url',
                                 'thumbnail_url', 'stacks'])


def read_file(path, rendered_text=True, branch=u'master', use_cache=True,
              timeout=cache.DEFAULT_CACHE_TIMEOUT):
    """
    Read file contents

    :param path: Short path to file, not including repo or owner
    :param rendered_text: Read rendered markdown text (True) or raw text (False)
    :param branch: Name of branch to read file from
    :param use_cache: Boolean to read from cache if available and save if not
                      found in cache (use False to bypass any cache
                      interaction, useful for very large files)
    :param timeout: Cache timeout to save contents with (in seconds) - only
                    used if use_cache is True
    :returns: Text of file or None if file could not be read
    """

    if use_cache:
        text = cache.read_file(path, branch)
        if text is not None:
            return json.loads(text)

    details = read_file_details(path, rendered_text=rendered_text,
                                branch=branch)
    if details is None:
        return None

    if use_cache:
        cache.save_file(path, branch, json.dumps(details.text), timeout=timeout)

    return details.text


def read_file_details(path, rendered_text=True, branch=u'master'):
    """
    Read file details including SHA and contents

    :param path: Short path to file, not including repo or owner
    :param rendered_text: Read rendered markdown text (True) or raw text (False)
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


def in_review_article_path():
    """
    Get path to in-review article file listing

    :returns: Path to in-review article file listing file
    """

    return '%s/%s' % (remote.default_repo_path(), IN_REVIEW_FILENAME)


def draft_article_path():
    """
    Get path to draft article file listing

    :returns: Path to draft article file listing file
    """

    return '%s/%s' % (remote.default_repo_path(), DRAFT_FILENAME)


def published_articles(branch=u'master'):
    """
    Get iterator through list of published articles from file listing

    :param branch: Name of branch to save file listing to
    :returns: Generator to iterate through file_listing_item tuples
    """

    return _read_file_listing(PUB_FILENAME, branch=branch)


def in_review_articles(branch=u'master'):
    """
    Get iterator through list of in-review articles from file listing

    :param branch: Name of branch to save file listing to
    :returns: Generator to iterate through file_listing_item tuples
    """

    return _read_file_listing(IN_REVIEW_FILENAME, branch=branch)


def draft_articles(branch=u'master'):
    """
    Get iterator through list of draft articles from file listing

    :param branch: Name of branch to save file listing to
    :returns: Generator to iterate through file_listing_item tuples
    """

    return _read_file_listing(DRAFT_FILENAME, branch=branch)


def read_redirects(branch=u'master'):
    """
    Read redirects file and parse into a dictionary mapping an old url to a new
    url

    :param branch: Branch to read redirect file from
    :returns: Dictionary with keys for old url and values for new url

    The format of the redirect file is two URLs per line with whitespace
    between them::

        http://www.xyz.com http://www.xyz.com/1
        http://www.xyz.com/2 http://www.xyz.com/3

    This means redirect http://www.xyz.com to http://www.xyz.com/1 and redirect
    http://www.xyz.com/2 to http://www.xyz.com/3.

    Each line can start with an optional '- ', which will be ignored.

    Any lines starting with a '#' or not containing two tokens is ignored.
    """

    redirects = {}

    # This should be a pretty low volume file so cache it for an hour.
    text = read_file(REDIRECT_FILENAME, rendered_text=False, branch=branch,
                     use_cache=True, timeout=60 * 60)
    if not text:
        return redirects

    for line in text.splitlines():
        if line.startswith('#'):
            continue

        tokens = line.split()

        # A valid line is either 3 tokens one of which is a '-' to start a
        # markdown list item or 2 tokens (old and new url).
        if len(tokens) == 3 and tokens[0] == '-':
            old = tokens[1]
            new = tokens[2]
        elif len(tokens) == 2:
            old = tokens[0]
            new = tokens[1]
        else:
            # Not valid line, needs at least 2 tokens
            continue

        redirects[old] = new

    return redirects


def update_article_listing(article_url, title, author_url, author_name,
                           committer_name, committer_email,
                           author_img_url=None, thumbnail_url=None,
                           stacks=None, branch=u'master', status=DRAFT):
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
    :param status: PUBLISHED, IN_REVIEW, or DRAFT to add article to file
                   listing.  All other file listings will also be updated to
                   remove this article if it exists there.

    :returns: True or False if file listing was updated
    """

    if status == PUBLISHED:
        path_to_listing = published_article_path()
        filename = PUB_FILENAME
        message = u'Adding "%s" to published' % (title)
    elif status == IN_REVIEW:
        path_to_listing = in_review_article_path()
        filename = IN_REVIEW_FILENAME
        message = u'Adding "%s" to in-review' % (title)
    else:
        path_to_listing = draft_article_path()
        filename = DRAFT_FILENAME
        message = u'Adding "%s" to draft' % (title)

    sha = None
    start_text = ''

    details = read_file_details(filename, rendered_text=False, branch=branch)
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

    if start_text != text:
        commit_sha = remote.commit_file_to_github(path_to_listing, message,
                                                  text, committer_name,
                                                  committer_email, sha=sha,
                                                  branch=branch)
        if commit_sha is None:
            return False

    cache.delete_file(filename, branch)

    # Now update the opposite files so the article is only on 1 file at a time
    results = []
    for possible_status in (PUBLISHED, IN_REVIEW, DRAFT):
        if possible_status == status:
            continue

        # Don't care about status here we need to try all the possible files
        # and lower levels will log anything useful
        res = remove_article_from_listing(title, possible_status,
                                          committer_name, committer_email,
                                          branch=branch)
        results.append(res)

    return all(results)


def remove_article_from_listing(title, status, committer_name,
                                committer_email, branch=u'master'):
    """
    Remove article title from file listing

    :param title: Title of article to remove from listing
    :param status: PUBLISHED, IN_REVIEW, or DRAFT
    :param committer_name: Name of user committing change
    :param committer_email: Email of user committing change
    :param branch: Name of branch to save file listing to
    :returns: True or False if file listing was updated
    """

    if status == PUBLISHED:
        path_to_listing = published_article_path()
        filename = PUB_FILENAME
        message = u'Removing "%s" from published' % (title)
    elif status == IN_REVIEW:
        path_to_listing = in_review_article_path()
        filename = IN_REVIEW_FILENAME
        message = u'Removing "%s" from in-review' % (title)
    else:
        path_to_listing = draft_article_path()
        filename = DRAFT_FILENAME
        message = u'Removing "%s" from draft' % (title)

    sha = None
    start_text = ''

    details = read_file_details(filename, rendered_text=False, branch=branch)
    if details is not None:
        sha = details.sha
        start_text = details.text

    text = get_removed_file_listing_text(start_text, title)

    if start_text != text:
        commit_sha = remote.commit_file_to_github(path_to_listing, message,
                                                  text, committer_name,
                                                  committer_email, sha=sha,
                                                  branch=branch)
        if commit_sha is None:
            return False

    cache.delete_file(filename, branch)

    return True


def sync_file_listing(all_articles, status, committer_name, committer_email,
                      branch=u'master'):
    """
    Synchronize file listing file with contents of repo

    :param all_articles: Iterable of article objects that should be synced to
                         listing
    :param status: PUBLISHED, IN_REVIEW, or DRAFT
    :param committer_name: Name of user committing change
    :param committer_email: Email of user committing change
    :param branch: Name of branch to save file listing to
    :returns: Boolean to indicate if syncing succeeded or failed

    This can be a very expensive operation because it heavily calls the remote
    API so be careful calling this for API limits and performance.  Ideally
    this should at least be run as some kind of background process.
    """

    if status == PUBLISHED:
        path_to_listing = published_article_path()
        filename = PUB_FILENAME
        message = u'Synchronizing published'
    elif status == IN_REVIEW:
        path_to_listing = in_review_article_path()
        filename = IN_REVIEW_FILENAME
        message = u'Synchronizing in-review'
    else:
        path_to_listing = draft_article_path()
        filename = DRAFT_FILENAME
        message = u'Synchronizing draft'

    text = u''
    sha = None

    details = read_file_details(filename, rendered_text=False, branch=branch)
    if details is not None:
        text = details.text
        sha = details.sha

    start_text = text

    # Get listing of all the titles currently in the file so we know which ones
    # to remove and we'll try to remove them in order so the diff of the file
    # is sane.
    prev_titles = {item.title for item in read_items_from_file_listing(text)}
    curr_titles = set()

    for article in all_articles:
        article_url = filters.url_for_article(article,
                                              base_url=app.config['DOMAIN'])
        author_url = filters.url_for_user(article.author_name,
                                          base_url=app.config['DOMAIN'])

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
        commit_sha = remote.commit_file_to_github(path_to_listing, message,
                                                  text, committer_name,
                                                  committer_email, sha=sha,
                                                  branch=branch)
        if commit_sha is None:
            return False
    else:
        app.logger.debug('Listing unchanged so no commit being made')

    cache.delete_file(filename, branch)

    return True


def _read_file_listing(filename, branch=u'master'):
    """
    Get iterator through list of articles from file

    :param filename: Short status path to file not including repo or owner
    :param branch: Name of branch to save file listing to
    :returns: Generator to iterate through file_listing_item tuples
    """

    text = read_file(filename, rendered_text=False, branch=branch,
                     use_cache=True)
    if text is None:
        raise StopIteration

    for item in read_items_from_file_listing(text):
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


def read_items_from_file_listing(text):
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

    return [_force_unicode(m.group()) for m in STACK_RE.finditer(line.lower())]


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

    # New content goes at front i.e. top of file so need to push efficiently on
    # both ends.
    new_contents = collections.deque()
    changed_section = False

    for lines in _iter_article_sections_from_file_listing(text):
        # Always put a newline in when we add something b/c we add 1 'section'
        # at a time and always want those separated by a blank line b/c it
        # renders better on github that way.
        if new_contents:
            new_contents.append(u'\n\n')

        # Already found the line we need to replace so just copy remainder of
        # text to new contents and we'll write it out.
        if changed_section:
            new_contents.append(u'\n'.join(lines))
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

            new_contents.append(new_text)
        else:
            new_contents.append(u'\n'.join(lines))

    # Must be a new article section
    if not changed_section:
        new_text = _file_listing_to_markdown(article_url, title, author_url,
                                             author_name, author_img_url,
                                             thumbnail_url, stacks)
        # Make sure we already have text that we need to separate with a new
        # line
        if new_contents:
            new_contents.appendleft(u'\n\n')

        new_contents.appendleft(new_text)

    return u''.join(new_contents)


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

        new_lines.append(u'\n'.join(lines))
        new_lines.append(u'\n\n')

    # Don't need extra newlines at the end of file
    if new_lines and new_lines[-1] == u'\n\n':
        new_lines.pop()

    return u''.join(new_lines)
