"""
Script to print out subscribers from a mailchimp list
"""

import argparse
import collections
import csv
import textwrap
import pprint
import sys

import mailchimp


def main(api_key, list_id, group=None, interests=None, just_interests=False):
    """
    Get dictionary of subscribers from based on query parameters

    :param api_key: Mailchimp API key
    :param list_id: Mailchimp list ID to query
    :param group: Name of Mailchimp group to query (if None all list
                  subscribers are returned as a dictionary)
    :param interests: List of interests under given group to query (if None
                      subscribers are returned as a dictionary)
    :param just_interests: Boolean to include only list of interests that users
                           are actually interested in

    :returns: Dictionary of subscriber data
    """

    subscribers = get_subscribers(api_key, list_id)

    if not subscribers:
        return {}

    if group is None:
        if just_interests:
            return filter_interests(subscribers)
        else:
            return subscribers

    return query_subscribers(subscribers, group, interests)


def filter_interests(subscribers):
    """
    Generator to iterate through subscribers filtered by only their interests

    :param subscribers: Dict as returned from get_subscribers()

    :returns: iterator through dicts with email as key and value as list of
              interests
    """


    for subscriber in subscribers:
        subscribers_subset = collections.defaultdict(list)

        for g in subscriber['merges']['GROUPINGS']:
            email = subscriber['merges']['EMAIL']

            for interest in g['groups']:
                if interest['interested']:
                    subscribers_subset[email].append(interest['name'])

        if subscribers_subset:
            yield subscribers_subset


def query_subscribers(subscribers, group, interests=None):
    """
    Iterator through subscribers based on query parameters

    :param subscribers: Dictionary of subscribers to query (as returned from
                        Mailchimp API)
    :param group: Name of Mailchimp group to query (if None all list
                  subscribers are returned as a dictionary)
    :param interests: List of interests under given group to query (if None
                      subscribers are returned as a dictionary)

    :returns: Iterator through dictionary of subscriber data
    """

    for subscriber in subscribers:
        subscribers_subset = collections.defaultdict(list)

        for g in subscriber['merges']['GROUPINGS']:
            if g['name'] != group:
                continue

            email = subscriber['merges']['EMAIL']

            if interests is None:
                # Grab all interests for group
                for interest in g['groups']:
                    if interest['interested']:
                        subscribers_subset[email].append(interest['name'])

                continue

            for interest in g['groups']:
                if interest['name'] in interests and interest['interested']:
                    subscribers_subset[email].append(interest['name'])
                    break

        if subscribers_subset:
            yield subscribers_subset


def get_subscribers(api_key, list_id):
    """
    Generator through subscribers dicts as paginated from Mailchimp API

    :param api_key: Mailchimp API key
    :param list_id: Mailchimp list ID to query

    :returns: Iterator of Dict of subscribers from Mailchimp
              /lists/{list_id}/members/ API
    """

    mc = mailchimp.Mailchimp(api_key)

    page = 0
    total_read = 0
    total_available = None

    # This is the max mailchimp will let us pull with a single request
    opts = {'limit': 100, 'start': page}

    while True:
        subs = mc.lists.members(list_id, opts=opts)
        if total_available is None:
            total_available = subs['total']

        if not subs['data']:
            raise StopIteration

        for sub in subs['data']:
            yield sub

        total_read += len(subs)

        if total_read >= total_available:
            raise StopIteration

        opts['start'] += 1


def _parse_args():
    desc = textwrap.dedent("""
    Script to print out CSV listing of mailchimp subscribers. The output format
    when using --just-interests (default) is suitable for redirecting to a file
    for importing to Mailchimp.  For example:

    python mailchimp_subscribers.py -k <key> -l <list_id> > subscribers.csv

    python mailchimp_subscribers.py -k <key> -l <list_id> -g favorite-languages -i "ruby,rails" > rails_subs.csv
    """)

    parser = argparse.ArgumentParser(
                        prog=__file__,
                        description=desc,
                        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument('-k', '--api-key', action='store', dest='api_key',
                        required=True, help='API key for mailchimp')

    parser.add_argument('-l', '--list-id', action='store', dest='list_id',
                        required=True, help='List ID to print subscribers from')

    parser.add_argument('-g', '--group', action='store', dest='group',
                        required=False, default=None,
                        help='Name of group to query')

    parser.add_argument('-i', '--interests', action='store', dest='interests',
                        required=False, default=None,
                        help='CSV list of interests to query (enclose interests with spaces inside quotes)')

    parser.add_argument('--just-interests', action='store_true',
                        dest='just_interests', required=False, default=True,
                        help='Print just the interests for each subscriber')

    args = vars(parser.parse_args())
    if args['interests'] is not None:
        args['interests'] = args['interests'].split(',')

    return args


def print_subscribers_as_csv(subs, group=None):
    """
    Print subscribers to stdout in CSV format

    :param subs: List of subscribers as returned by main()
    :param group: Optional name of group to print in CSV header
    :returns: None
    """

    if group is None:
        group = 'interests'

    writer = csv.writer(sys.stdout)
    writer.writerow(['email', group])

    for subscriber in subs:
        for email, interests in subscriber.iteritems():
            row = [email]
            row.extend(interests)
            writer.writerow(row)


def pretty_print_subscribers(subs):
    """
    Print subscriber info to stdout in pretty printed dict-style

    :param subs: List of subscribers as returned by main()
    :returns: None
    """

    pp = pprint.PrettyPrinter(indent=4)
    for subscriber in subs:
        pp.pprint(subscriber)


if __name__ == '__main__':
    args = _parse_args()

    subs = main(args['api_key'], args['list_id'], args['group'],
                args['interests'], args['just_interests'])

    # Hack to allow us to get all data from Mailchimp API if no query params
    # are used
    if not args['just_interests']:
        pretty_print_subscribers(subs)
    else:
        print_subscribers_as_csv(subs, group=args['group'])
