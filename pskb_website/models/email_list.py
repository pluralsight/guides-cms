"""
Thin wrapper around mailchimp API for common tasks
"""

import mailchimp

from .. import app

# Save the group names in memory so we don't have to fetch them every time we
# add a subscriber.  This means we'll have to reboot the app if we ever modify
# the groups, but at this time it's worth it to make subscribing faster.
FAVORITE_STACKS = set()

try:
    MC = mailchimp.Mailchimp(app.config['MAILCHIMP_API_KEY'])
except mailchimp.Error as err:
    app.logger.warning('Unable to setup mailchimp API if you want to use the email subscribe functionality: %s', err)
    MC = None

LIST_ID = app.config['MAILCHIMP_LIST_ID']
FAVORITE_STACKS_NAME = app.config['MAILCHIMP_STACKS_GROUP_NAME']


def add_subscriber(email, stacks):
    """
    Add subscriber to mailchimp list

    :param email: Email of subscriber
    :param stacks: List of programming 'stacks' to association with subscriber

    :returns: Subscriber ID or None if subscriber was not added
    """

    initialize_favorite_stacks(LIST_ID)

    # Weed out any stacks that are not already in mailchimp list groups
    groups = []
    valid_stacks = list(set(stacks).intersection(FAVORITE_STACKS))
    groups = [{'name': FAVORITE_STACKS_NAME, 'groups': valid_stacks}]

    # Mailchimp API requires this to be in a dict
    email = {'email': email}

    # The 'groupings' is a special key in the API merge_vars dict that's
    # required to add subscribers to a group.
    merge_vars = {'groupings': groups}

    try:
        subscriber_id = MC.lists.subscribe(LIST_ID,
                                           email,
                                           merge_vars=merge_vars,
                                           double_optin=False,
                                           update_existing=True,
                                           replace_interests=True)
    except Exception as err:
        app.logger.error('Failed adding subscriber: %s (list: "%s", email: "%s", stacks: "%s", groups: "%s")',
                         err, LIST_ID, email, stacks, groups, exc_info=True)
        return None

    return subscriber_id


def initialize_favorite_stacks(list_id):
    """
    Initialize global favorite stacks dictionary
    """

    global FAVORITE_STACKS

    if FAVORITE_STACKS:
        return

    groups = get_groups(list_id).keys()
    if groups:
        FAVORITE_STACKS = groups


def get_groups(list_id):
    """
    Get dictionary mapping group names to group ids

    :param list_id: List ID

    :returns: Dictionary mapping each group name to group id
    """

    full_group_info = {}

    if MC is None:
        return full_group_info

    try:
        result = MC.lists.interest_groupings(list_id)
    except ValueError:
        app.logger.error('Failed getting groups from mailchimp (list: "%s")',
                         list_id,
                         exc_info=True)
        return full_group_info


    try:
        full_group_info = result[0]['groups']
    except (KeyError, IndexError):
        app.logger.error('Failing reading groups from mailchimp response: %s',
                         result)

    groups = {}
    for group in full_group_info:
        groups[group['name']] = group['id']

    return groups
