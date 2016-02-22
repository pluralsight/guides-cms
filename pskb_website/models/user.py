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
    """

    user_info = cache.read_user(username)
    if user_info is not None:
        return User.from_json(user_info)

    user_info = remote.read_user_from_github(username)
    if not user_info:
        return None

    # This doesn't take a username b/c it's only accessible via the logged in
    # user, which the remote layer can tell from the session.
    email = remote.primary_github_email_of_logged_in()
    user = User(user_info['name'], user_info['login'], email,
                user_info['avatar_url'], user_info['bio'])

    # User a longer timeout b/c not anticipating user's name, bio or
    # collaborator status to change very often
    cache.save_user(user.login, lib.to_json(user), timeout=60 * 30)
    return user


class User(object):
    """Object representing user"""

    def __init__(self, name, login, email=None, avatar_url=None, bio=None):
        """
        Initialize user

        :param name: Name of user
        :param login: Login/username of user
        :param email: Email of user
        :param avatar_url: URL to avatar/image for user
        :param bio: Biography text of user
        """

        self.name = name
        self.login = login
        self.email = email
        self.avatar_url = avatar_url
        self.bio = bio
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
