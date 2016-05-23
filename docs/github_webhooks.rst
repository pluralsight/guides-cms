===============
Github Webhooks
===============

The CMS uses `Github webhooks <https://developer.github.com/webhooks/>`_ to
get notifications of changes happening on Github.com.  These are not required,
but they are useful if you're using the built-in :ref:`Caching <redis_caching>`.
These webhooks can clear the cache when something changes on Github.com
directly so that the CMS is always using the most up-to-date guide information.

Configuring Push Events
-----------------------

This event is used to clear the cache of a guide when it's changed via a commit
from the Github API and/or Github.com

1. Go to the settings area of your content repository where all of your guides
   are stored and click on 'Webhooks & services'.
2. Click 'Add webhook'
3. Set the `Payload URL` to `<your_domain>/github_push`
4. The `Content type` should be `application/json`
5. **Leave `Secret` blank**
6. Only subscribe to the push event
7. Make sure the webhook is marked as **active**
8. Click 'Add webhook'

Configuring Delete Events
-------------------------

This event is used to clean up the list of branches associated with a guide.

1. Go to the settings area of your content repository where all of your guides
   are stored and click on 'Webhooks & services'.
2. Click 'Add webhook'
3. Set the `Payload URL` to `<your_domain>/github_push`
4. The `Content type` should be `application/json`
5. **Leave `Secret` blank**
6. Only subscript to the delete event
    - Click 'Let me select individual events'
7. Make sure the webhook is marked as **active**
8. Click 'Add webhook'


Testing
-------

Github has `great documentation on testing webhooks <https://developer.github.com/webhooks/testing/>`_ and `a solution for testing locally <https://developer.github.com/webhooks/creating>`_.
