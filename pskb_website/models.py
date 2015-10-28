"""
Models for PSKB
"""

from . import db


article_tags = db.Table('article_tags',
    db.Column('tag_id', db.Integer, db.ForeignKey('tags.id')),
    db.Column('article_id', db.Integer, db.ForeignKey('articles.id'))
)


class Article(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())

    github_id = db.Column(db.String())
    author_id = db.Column(db.Integer, db.ForeignKey('users.id'))

    tags = db.relationship('Tag', secondary=article_tags,
                           backref=db.backref('articles', lazy='dynamic'))

    def __init__(self, title, author_id, github_id):
        self.title = title
        self.author_id = author_id
        self.github_id = github_id

    def __repr__(self):
        return '<id %d title: %s>' % (self.id, self.title)


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
    github_username = db.Column(db.String())
    articles = db.relationship('Article', backref='user', lazy='dynamic')

    def __init__(self, github_username):
        self.github_username = github_username

    def __repr__(self):
        return '<id %d github_username: %s>' % (self.id, self.github_username)


class Tag(db.Model):
    __tablename__ = 'tags'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50))

    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return '<id %d name: %s>' % (self.id, self.name)
