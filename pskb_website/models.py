"""
Models for PSKB
"""

from . import app
from . import db
from . import utils


def main_article_path():
    """Get path to main repo"""

    return '%s/%s' % (app.config['REPO_OWNER'], app.config['REPO_NAME'])


class Article():
    def __init__(self, title, author_name, language,
                 repo_path=None, branch='master', filename='article.md'):
        self.title = title
        self.author_name = author_name
        self.language = language

        self.repo_path = repo_path
        if self.repo_path is None:
            self.repo_path = main_article_path()

        self.branch = branch
        self.filename = filename

        self.path = '%s/%s/%s' % (self.language, utils.slugify(self.title),
                                  self.filename)

    def __repr__(self):
        return '<author_name: %s title: %s>' % (self.author_name, self.title)

    @property
    def github_url(self):
        """Return url for viewing content directly on github site"""

        return 'https://github.com/%s/blob/%s/%s' % (self.repo_path,
                                                     self.branch,
                                                     self.path)


# FIXME: Not sure what all we want here b/c we might want to include some
# pluralsight username or something along with other social account names?
# Benefits:
#   - Don't have to keep track of and update if it changes.
#       - i.e. github access tokens, we just use them as sessions and if
#         github ever changes it we're ok
#       - Also no security risk by storing the token.
#           - This might not be a huge risk since attackers would still
#             have to have our client id and client secret to use the
#             access token, but still...
#   - Save our own storage space..
# Downsides:
# ?

class User(db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    github_username = db.Column(db.String(), unique=True)
    email = db.Column(db.String(), unique=True)

    def __init__(self, github_username, email):
        self.github_username = github_username
        self.email = email

    def __repr__(self):
        return '<id %s github_username: %s>' % (self.id, self.github_username)
