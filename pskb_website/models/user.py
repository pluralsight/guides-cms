"""
User related model code
"""

import json

from .. import remote
from .. import cache
from . import lib


def find_user(username=None):
    """
    Find a user object with given username

    :param username: Optional username to search for, if no username given the
                     currently logged in user will be returned (if any)
    :returns: User object

    Note the email field on the returned user object is only valid when reading
    the logged in user (i.e. when NOT passing a username). We cannot read email
    information for users who have not authenticated the application.
    """

    if username is not None:
        user_info = cache.read_user(username)
        if user_info is not None:
            return User.from_json(user_info)

    user_info = remote.read_user_from_github(username)
    if not user_info:
        return None

    user = User(user_info['name'], user_info['login'])

    # Request is for logged in user only
    if username is None:
        email = remote.primary_github_email_of_logged_in()
        user.email = email

    user.avatar_url = user_info['avatar_url']
    user.location = user_info['location']
    user.blog = user_info['blog']

    # Github has added and removed support for bio so be careful
    try:
        user.bio = user_info['bio']
    except KeyError:
        pass

    # User a longer timeout b/c not anticipating user's name,etc. to change
    # very often
    cache.save_user(user.login, lib.to_json(user), timeout=60 * 30)
    return user


class User(object):
    """Object representing user"""

    def __init__(self, name, login):
        """
        Initialize user

        :param name: Name of user
        :param login: Login/username of user
        """

        self.name = name or login
        self.login = login
        self.email = None
        self.avatar_url = None
        self.bio = None
        self.location = None
        self.blog = None
        self._is_collaborator = None

    def __repr__(self):
        return '<login: %s>' % (self.login)

    @property
    def is_collaborator(self, owner=None, repo=None):
        """
        Determine if user is a collaborator on repo

        :param owner: Owner of repository defaults to REPO_OWNER config value
        :param repo: Name of repository defaults to REPO_NAME config value
        """

        if self._is_collaborator is not None:
            return self._is_collaborator

        for login in remote.read_repo_collaborators_from_github(owner, repo):
            if login == self.login:
                return True

        return False

    @is_collaborator.setter
    def is_collaborator(self, value):
        """
        Set if user is collaborator
        :param value: True or False
        """

        self._is_collaborator = value

    @staticmethod
    def from_json(str_):
        """
        Create user object from json string

        :param str_: json string representing user
        :returns: User object
        """

        dict_ = json.loads(str_)

        # Required arguments
        name = dict_.pop('name', None)
        login = dict_.pop('login', None)

        user = User(name, login)
        for attr, value in dict_.iteritems():
            setattr(user, attr, value)

        return user
