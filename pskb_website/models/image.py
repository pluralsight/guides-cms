"""
Save and read image files to/from github
"""

import os
import uuid

from werkzeug import secure_filename

from .. import app
from ..remote import commit_image_to_github


IMAGE_DIR = 'images'

def main_image_path():
    """Get path to main repos images"""

    return '%s/%s/%s/' % (app.config['REPO_OWNER'],
                          app.config['REPO_NAME'],
                          IMAGE_DIR)


def github_url_from_upload_path(path, name, branch='master'):
    """
    Get URL to see raw image on github from the path the file was uploaded to

    :param path: Path Full path file was save to github with
    :param name: Name file was saved with
    :param branch: Branch image was saved to
    :returns: URL to see content on github
    """

    path = main_image_path()

    tokens = []
    for t in path.split('/'):
        t = t.strip()
        if not t:
            continue

        tokens.append(t)

    assert len(tokens) == 3, 'Image path must have repo owner, name, and directory'

    path_w_branch = '%s/%s/%s/%s' % (tokens[0], tokens[1], branch, tokens[2])

    # Use https:// b/c with just http:// github's own file view won't render
    # the link on pages like:
    # https://github.com/durden/articles/blob/master/uploading-image/article.md)
    return 'https://raw.githubusercontent.com/%s/%s' % (path_w_branch, name)


def save_image(file_, extension, message, name, email, branch='master'):
    """
    Save image to github as a commit

    :param file_: Open file object containing image
    :param: Extension to use for saved filename
    :param message: Commit message to save image with
    :param name: Name of user committing image
    :param email: Email address of user committing image
    :param branch: Branch to save image to
    :returns: Public URL to image or None if not successfully saved
    """

    file_name = secure_filename('%s%s%s' % (str(uuid.uuid4()), os.extsep, extension))
    path = os.path.join(main_image_path(), file_name)
    url = None

    if commit_image_to_github(path, message, file_, name, email,
                              branch=branch) is not None:

        url = github_url_from_upload_path(path, file_name, branch=branch)

    return url
