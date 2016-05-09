#!/usr/bin/env python

"""
Script to print out Github API rate limit for REPO_OWNER user i.e. the main
github user account used for the guides-cms application.
"""

import argparse
from datetime import datetime
import requests

DOMAIN = 'http://tutorials.pluralsight.com/'
URL = '/gh_rate_limit'


def main(domain):
    response = get_rate_limit(domain)
    if response:
        pprint(response)


def get_rate_limit(domain=DOMAIN):
    """Get rate limit as dictionary"""

    url = '%s%s' % (domain, URL)
    resp = requests.get(url)

    if resp.status_code == 200:
        return resp.json()
    else:
        print 'Failed checking rate limit, status_code: %d' % (resp.status_code)
        return {}


def pprint(rate_limit):
    """
    Pretty print rate limit dictionary to be easily parsable and readable
    across multiple lines
    """

    # Ignoring the 'rate' key b/c github API claims this will be removed in
    # next major version:
    # https://developer.github.com/v3/rate_limit/#deprecation-notice

    def print_(name, limits):
        date_ = datetime.utcfromtimestamp(limits[name]['reset'])
        print '%8s remaining: %4s limit: %4s reset: %s' % (
                name,
                limits[name]['remaining'],
                limits[name]['limit'],
                date_.strftime('%d-%m-%Y %H:%M:%S'))

    print_('core', rate_limit['resources'])
    print_('search', rate_limit['resources'])

    #u'resources': {u'core': {u'reset': 1462781427, u'limit': 5000, u'remaining': 4923}, u'search': {u'reset': 1462780271, u'limit': 30, u'remaining': 30}}}

def _parse_args():
    """Parse args and get dictionary back"""

    parser = argparse.ArgumentParser(description='Get Github.com rate limit')
    parser.add_argument('-d', '--domain', action='store', required=False,
                        default=DOMAIN,
                        help='Domain to ping for rate limit JSON response (default: %s)' % (DOMAIN))

    # Turn odd argparse namespace object into a plain dict
    return vars(parser.parse_args())


if __name__ == '__main__':
    main(_parse_args()['domain'])
