"""
Models for PSKB
"""

from . import db


class Article(db.Model):
    __tablename__ = 'articles'

    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String())

    def __init__(self, title):
        self.title = title

    def __repr__(self):
        return '<id %d>' % (self.id)
