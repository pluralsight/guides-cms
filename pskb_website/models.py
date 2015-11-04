"""
Models for PSKB
"""

from . import db
from . import utils


article_tags = db.Table('article_tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id')),
    db.Column('article_id', db.Integer, db.ForeignKey('articles.id'))
)


class Article(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())
    path = db.Column(db.String())

    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    repo_id = db.Column(db.Integer, db.ForeignKey('repos.id'))

    repo = db.relationship('Repo')
    tags = db.relationship('Tag', secondary=article_tags,
                           backref=db.backref('articles', lazy='dynamic'))

    def __init__(self, title, author_id, repo_id, filename='article.md'):
        self.title = title
        self.author_id = author_id
        self.repo_id = repo_id
        self.filename = filename

        # Cannot set this yet b/c it includes the id
        self.path = None

    # FIXME: Can we somehow hide this on a session commit event or something?
    # It's clunky that the user has to call commit twice.
    def update_path(self):
        """
        Set path of article

        This must be done after committing an article to the database b/c it
        requires an id.
        """

        # Add the article id to the slugified title so we can support duplicate
        # titles across entire repo.  Otherwise the slugified title could only
        # be used once.  The other alternative would be to use the user id, but
        # then each user could only have the title once. Probably not a big
        # deal but going for maximum flexibility here; and it's easy.
        directory = '%s-%d' % (utils.slugify(self.title), self.id)
        self.path = '%s/%s' % (directory, self.filename)

    def __repr__(self):
        return '<id %s title: %s>' % (self.id, self.title)

    @property
    def github_api_location(self):
        """
        Return full path more suited to calling Github API that includes the
        owner and repo info
        """

        return '%s/%s/contents/%s' % (self.repo.owner, self.repo.name, self.path)

    @property
    def github_url(self):
        """Return url for viewing content directly on github site"""

        return 'https://github.com/%s/%s/blob/master/%s' % (self.repo.owner,
                                                            self.repo.name,
                                                            self.path)


class Repo(db.Model):
    __tablename__ = 'repos'

    id = db.Column(db.Integer, primary_key=True)
    owner = db.Column(db.String(64), unique=True)
    name = db.Column(db.String(64))
    branch = db.Column(db.String(64))

    def __init__(self, owner, name, branch='master'):
        self.owner = owner
        self.name = name
        self.branch = branch


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
    articles = db.relationship('Article', backref='user', lazy='dynamic')

    def __init__(self, github_username, email):
        self.github_username = github_username
        self.email = email

    def __repr__(self):
        return '<id %d github_username: %s>' % (self.id, self.github_username)


class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True)

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<id %d name: %s>' % (self.id, self.name)
