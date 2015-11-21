"""
More direct wrapper around reading files from remote storage

This module serves as a small abstraction away from the remote storage so it
can easily be switched if needed while keeping the API the same.
"""

from .article import main_article_path
from ..remote import read_file_from_github


def read_file(path, rendered_text=True, branch='master'):
    """
    Read file

    :param path: Short path to file, not including repo or owner
    :param branch: Name of branch to read file from
    :returns: Raw or HTML rendered text of file
    """

    full_path = '%s/%s' % (main_article_path(), path)
    text, sha, github_url = read_file_from_github(full_path, branch, rendered_text)
    return text
