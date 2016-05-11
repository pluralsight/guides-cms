"""
Collection of functions for general use
"""

import os
from functools import wraps
from urlparse import urlparse

from flask import redirect, url_for, session, request, flash

from . import PUBLISHED
from . import app
from . import models


def is_logged_in():
    """
    Determine if user is logged in or not
    """

    return 'github_token' in session and 'login' in session


def login_required(func):
    """
    Decorator to require login and save URL for redirecting user after login
    """

    @wraps(func)
    def decorated_function(*args, **kwargs):
        """decorator args"""

        if not is_logged_in():
            # Save off the page so we can redirect them to what they were
            # trying to view after logging in.
            session['previously_requested_page'] = request.url

            return redirect(url_for('login'))

        return func(*args, **kwargs)

    return decorated_function


def collaborator_required(func):
    """
    Decorator to require login and logged in user to be collaborator

    This should be used instead of @login_required when the URL endpoint should
    be protected by login and the logged in user being a collaborator on the
    repo.  This will NOT redirect to login. It's meant to kick a user back to
    the homepage if they tried something they do not have permissions for.
    """

    @wraps(func)
    def decorated_function(*args, **kwargs):
        """decorator args"""

        if not is_logged_in():
            flash('Must be logged in', category='error')

            # Save off the page so we can redirect them to what they were
            # trying to view after logging in.
            session['previously_requested_page'] = request.url

            return redirect(url_for('index'))

        if 'collaborator' not in session or not session['collaborator']:
            flash('Must be a repo collaborator for that functionality.',
                  category='error')

            # Save off the page so we can redirect them to what they were
            # trying to view after logging in.
            session['previously_requested_page'] = request.url

            return redirect(url_for('index'))

        return func(*args, **kwargs)

    return decorated_function


def lookup_url_redirect(requested_url):
    """
    Lookup given URL for a 301 redirect

    :param requested_url: URL to look for a redirect
    :returns: URL to redirect to or None if no redirect found
    """

    new_url = None
    redirects = models.read_redirects()

    # All our URLs should be ASCII!
    try:
        old_url = str(requested_url)
    except UnicodeEncodeError:
        return None

    try:
        new_url = redirects[old_url]
    except KeyError:
        # Maybe the url was referenced without the domain:
        try:
            old_url = urlparse(old_url).path
        except Exception as err:
            app.logger.error(u'Failed parsing URL "%s" for redirect: %s',
                             old_url, err)
            return None

        try:
            new_url = redirects[old_url]
        except KeyError:
            # No worries, guess this really was a bad URL
            pass

    return new_url
