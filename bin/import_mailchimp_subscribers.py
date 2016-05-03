"""
Script to import mailchimp subscribers from a CSV file

The text file should be formatted like the following:

email,<group_name>
email,<CSV list of groups>

The first line is considered the header and should include the name of the
group that the list of groups belongs to.

For example:

email,favorite-stacks
xyz@acme.com,Python,.NET,C/C++
...

"""

import argparse
import csv

import mailchimp


def main(api_key, list_id, file_, dry_run=False):
    """
    :param api_key: Mailchimp API key
    :param list_id: Mailchimp list ID to add subscribers to
    :param file_: File to read subscribers from
    :param dry_run: Do a dry run and print the import data without importing

    :returns: None
    """

    mc = mailchimp.Mailchimp(api_key)
    return add_subscribers_from_file(mc, list_id, file_, dry_run)


def add_subscribers_from_file(api_instance, list_id, file_, dry_run=False):
    """
    Add subscribers from file

    :param api_instance: Instance of mailchimp.Mailchimp API object
    :param list_id: List ID to add subscribers to
    :param file_: File to read subscribers from
    :param dry_run: Do a dry run and print the import data without importing

    :returns: None
    """

    # FIXME: There are some API endpoints for batch operations, maybe we can
    # use these for better performance instead of adding one by one?

    for email, group_name, stacks in subscribers_from_file(file_):
        if dry_run:
            print email, stacks
        else:
            add_subscriber(api_instance, list_id, email, stacks, group_name)


def add_subscriber(api_instance, list_id, email, stacks, group_name):
    """
    Add subscriber to mailchimp list

    :param api_instance: Instance of mailchimp.Mailchimp API object
    :param list_id: List ID to add subscribers to
    :param email: Email of subscriber
    :param stacks: List of programming 'stacks' to association with subscriber
    :param group_name: Name of group in Mailchimp list that stacks belong to

    :returns: Subscriber ID or None if subscriber was not added
    """

    groups = [{'name': group_name, 'groups': stacks}]

    # Mailchimp API requires this to be in a dict
    email = {'email': email}

    # The 'groupings' is a special key in the API merge_vars dict that's
    # required to add subscribers to a group.
    merge_vars = {'groupings': groups}

    subscriber_id = api_instance.lists.subscribe(list_id,
                                                 email,
                                                 merge_vars=merge_vars,
                                                 double_optin=False,
                                                 update_existing=True,
                                                 replace_interests=True)
    return subscriber_id


def subscribers_from_file(file_):
    """
    Generator to read subscribers from file

    :param file_: File to read (should be in format described at top of file)
    :returns: Iterator of tuples of the form (email, group_name, stacks_list)
    """

    with open(file_, 'r') as file_obj:
        reader = csv.reader(file_obj)
        header = reader.next()
        group_name = header[1]

        for row in reader:
            email = row[0]
            stacks = row[1:]

            yield email, group_name, stacks


def _parse_args():
    parser = argparse.ArgumentParser(prog=__file__)

    parser.add_argument('-k', '--api-key', action='store', dest='api_key',
                        required=True, help='API key for mailchimp')

    parser.add_argument('-l', '--list-id', action='store', dest='list_id',
                        required=True, help='List ID to add subscribers to')

    parser.add_argument('--dry-run', action='store_true', dest='dry_run',
                        required=False, default=False, help='Do a dry run and just print what would be imported without actually importing')

    parser.add_argument('-f', '--file', action='store', dest='import_file',
                        required=True, help='File containing information to, input file should have one subscriber per line, see file header for more details on format')

    return vars(parser.parse_args())


if __name__ == '__main__':
    args = _parse_args()
    main(args['api_key'], args['list_id'], args['import_file'], args['dry_run'])
