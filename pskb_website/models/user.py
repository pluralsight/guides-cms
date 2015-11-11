"""
User related model code
"""

from .. import remote


def find_user(username=None):
    """
    Find a user object with given username

    :param username: Optional username to search for, if no username given the
                     currently logged in user will be returned (if any)
    :returns: User object
    """

    user_info = remote.read_user_from_github(username)
    if not user_info:
        return None

    # This doesn't take a username b/c it's only accessible via the logged in
    # user, which the remote layer can tell from the session.
    email = remote.primary_github_email_of_logged_in()
    return User(user_info['name'], user_info['login'], email,
                user_info['avatar_url'], user_info['bio'])


class User(object):
    def __init__(self, name, login, email=None, avatar_url=None, bio=None):
        self.name = name
        self.login = login
        self.email = email
        self.avatar_url = avatar_url
        self.bio = bio

    def __repr__(self):
        return '<login: %s>' % (self.login)
