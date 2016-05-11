#!/usr/bin/env python

"""
Script to print out Github API rate limit for REPO_OWNER user i.e. the main
github user account used for the guides-cms application.

This script will automatically report the rate limit data to the New Relic APM
service IF you have New Relic properly configured in your environment
variables.  See the New Relic help for how to properly set this up.
"""

import argparse
from datetime import datetime
import os

import requests

DOMAIN = 'http://tutorials.pluralsight.com/'
URL = '/gh_rate_limit'
BASE_NEW_RELIC_EVENTS_URL = 'https://insights-collector.newrelic.com/v1/accounts'


def main(domain, report_to_new_relic=False):
    response = get_rate_limit(domain)
    if not response:
        return

    pprint(response)

    if report_to_new_relic:
        report_new_relic_custom_events(response)


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


def report_new_relic_custom_events(rate_limit):
    """
    Report custom metrics for API requests used and limit with Github API to
    New Relic
    """

    acct_id = os.environ.get('NEW_RELIC_ACCT_ID')
    key = os.environ.get('NEW_RELIC_INSIGHTS_API_KEY')
    if acct_id is None or key is None:
        print 'Unable to sent events to New Relic without NEW_RELIC_ACCT_ID and NEW_RELIC_INSIGHT_API_KEY environment variables'
        return

    # Report used instead of remaining just to make bar graphs more
    # readable by seeing if there's a big gap between what's remaining.
    limit = rate_limit['resources']['core']['limit']
    used = limit - rate_limit['resources']['core']['remaining']
    percent_used = used / float(limit)

    event = {'eventType': 'GithubAPI', 'limit': limit, 'used': used,
             'percent_used': percent_used}

    # https://docs.newrelic.com/docs/insights/new-relic-insights/adding-querying-data/inserting-custom-events-insights-api

    url = '%s/%s/events' % (BASE_NEW_RELIC_EVENTS_URL, acct_id)
    headers = {'X-Insert-Key': key}

    resp = requests.post(url, json=event, headers=headers)
    if resp.status_code != 200:
        print 'Failed reporting to New Relic, status_code: %d' % (resp.status_code)

    # Tried using the newrelic custom events but always got errors about agent
    # not running, probably because we're running from a script and not the
    # actual wsgi app.
    #agent.record_custom_event('GithubAPI',
                              #{'Calls Limit': limit, 'Calls Used': used},
                              #agent.application())


def _parse_args():
    """Parse args and get dictionary back"""

    parser = argparse.ArgumentParser(description='Get Github.com rate limit')
    parser.add_argument('-d', '--domain', action='store', required=False,
                        default=DOMAIN,
                        help='Domain to ping for rate limit JSON response (default: %s)' % (DOMAIN))
    parser.add_argument('--report-to-new-relic', action='store_true',
                        default=False, dest='report_to_new_relic',
                        help='Enable automatic reporting to New Relic APM when environment variables are configured')

    # Turn odd argparse namespace object into a plain dict
    return vars(parser.parse_args())


if __name__ == '__main__':
    args = _parse_args()
    main(args['domain'], args['report_to_new_relic'])
