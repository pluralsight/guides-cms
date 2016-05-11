================
Github API usage
================

The CMS heavily uses the Github API.  All of the raw API interaction takes
places in :file:`pskb_website/remote.py`.

-----------------------
Logging API Rate Limits
-----------------------

The CMS uses authenticated API requests to ensure a higher rate limit, which
at the time of this writing is `5000 requests/hour <https://developer.github.com/v3/#rate-limiting>`_.  This is sufficient if caching and
`conditional requests <https://developer.github.com/v3/#conditional-requests>`_
are used.

It's worth noting that the limit is per user and per application.  Therefore,
the CMS can make 5000 API requests/hour on behalf of a user.  However, not all
requests can be made with a specific user.  For example, all requests to commit
data to the content repository use the `REPO_OWNER` Github API account.  This
is necessary because regular users do not have commit rights to the content
repository.  The requests using the `REPO_OWNER` Github API account are:

- Reading guides for a non-logged in user
- Committing guides to any branch
- Uploaded images for a guide

The `REPO_OWNER` account is the only account reasonably affected by the rate
limiting because typical usage will not lead to a logged-in user reading
thousands of guides in an hour.

It can be useful to monitor your usage since there's an upper limit.  You can
log the CMS' Github API usage with the `bin/rate_limit_watcher.py` script.
There are a few ways to automate this data collection.

Heroku Scheduler
----------------

You can use the `Heroku Scheduler <https://devcenter.heroku.com/articles/scheduler>`_
add on to run `bin/rate_limit_watcher.py`.  Just add this add-on to your
account and set the add-on to run `bin/rate_limit_watcher.py` with your own
arguments.

New Relic Insights
------------------

You can also graph your API usage overtime by using `Custom Events from New Relic <https://docs.newrelic.com/docs/insights/new-relic-insights/adding-querying-data/inserting-custom-events-insights-api>`_.
To do this you'll need to configure a few environment variables for your setup:

- `NEW_RELIC_ACCT_ID` - Your New Relic account ID
- `NEW_RELIC_INSIGHTS_API_KEY` - Your New Relic Insights API Key

You can get help finding these values by using `the official New Relic docs <https://docs.newrelic.com/docs/insights/new-relic-insights/adding-querying-data/inserting-custom-events-insights-api>`_.

Finally, run `bin/rate_limit_watcher.py --report-to-new-relic` to log your
usage to New Relic.

We're using the New Relic Insights API instead of New Relic custom metrics and
custom events because the timestamps of the Github API data is not that
critical.  The API limits do not need to be synchonized with all the other New
Relic data.  In addition, the Insights API is easier to use from a script
that's not embedded in the main WSGI application.
