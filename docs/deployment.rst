==========
Deployment
==========

Currently the application has only been deployed using `Heroku <http://www.heroku.com>`_
but there are no reasons it cannot be deployed to any hosting platform or
server that supports the `Flask framework <http://flask.pocoo.org>`_.

Heroku
======

Heroku has a `good guide for Python apps <https://devcenter.heroku.com/articles/getting-started-with-python#introduction>`_
that gives a nice overview of the concepts you'll need to know to get going,
but some of the specifics for this setup are slightly different.

`Real Python <https://realpython.com>`_ also has a `great guide on setting up a
basic flask app on Heroku <https://realpython.com/blog/python/flask-by-example-part-1-project-setup/>`_.

The following steps assume you have the basic `Heroku toolbelt installed <https://devcenter.heroku.com/articles/getting-started-with-python#set-up>`_.

1. Create `Heroku <http://heroku.com>`_ app
    * `heroku create [name]`
    * You can specify a name but it must be unique. You can also leave it blank
      and Heroku will create a unique name for you.
2. Add git remote for your app
    * `git remote add heroku git@heroku.com:<name>.git` where <name> is the
      name of your Heroku app from step 1.
3. Setup Heroku config
    * See example_config.py for a listing of the environment variables that
      must be setup in your Heroku config.
    * You'll have to wait to setup the `REPO_OWNER_TOKEN` variable until the application is fully running.
    * **Do not forget to set HEROKU=1 in the heroku environment variables!**
    * You can set Heroku config variables with the following syntax:
        * `heroku config:set REPO_NAME=<name>`
        * Or something like the following if you have multiple remotes for Heroku
        * `heroku config:set REPO_NAME=<name> --app pro`
        * `heroku config:set REPO_NAME=<name> --app stage`
4. `Setup Redis add-on for background jobs <celery_on_heroku>`
5. Deploy changes
    * `git push heroku master`
    * Or something like the following if you have multiple remotes for Heroku
    * `git push stage master` where <stage> is remote name for Heroku and
      master is local branch you want to push.
    * **Make sure your changes are committed locally first!**
6. Go to your `heroku dashboard settings <https://dashboard.heroku.com/>` resources for your app and verify the worker task is running.
7. Change the callback URL for your github application to the heroku URL
    * Typically something like `http://<app_name.herokuapp.com>/github/authorized`
8. Visit your running heroku application in the browser
    * URL will be something like `http://<app_name.herokuapp.com>/`
9. Login with your github account and authorize your newly created application
    * **Login with the account you set as the REPO_OWNER**
10. Check your logs for the new token printed. This will be a CRTICAL level log message.
11. Set the printed token equal to the `REPO_OWNER_ACCESS_TOKEN` environment
    variable
    * `heroku config:set REPO_OWNER_ACCESS_TOKEN=<token>`

By default the application will be served up by `Gunicorn <http://gunicorn.org>`_.

You can slightly improve your performance on Heroku by using setting the
`WEB_CONCURRENCY` environment variable, which gunicorn automatically honors.
You can set that variable with the following command:

* `heroku config:set WEB_CONCURRENCY=3`

You'll want to set this to something suitable for the size of your
`Heroku dyno <https://www.heroku.com/pricing>`_ and the memory requirements of
your the flask application.

--------------------------------------------
Run application locally with Heroku Procfile
--------------------------------------------

You'll need to complete the setup below for getting things running on Heroku
before doing this, or at least setting up your Heroku environment variables as
described below.  Then:

1. Run `heroku config --app <app_name>` to see all the configuration
2. Copy all the these configuration values into a file with the `key=value` format instead of `key:value` which is the output of the Heroku command.
3. Change the callback URL on your github application to `http://0.0.0.0:5000/`
4. Run `heroku local --env <file_from_step_2>`

Useful Heroku add-ons
---------------------

1. `Papertrail <https://elements.heroku.com/addons/papertrail>`_

* Provides bigger log for debugging issues and enables easy searching
* `Install the CLI tools <https://github.com/papertrail/papertrail-cli#readme>`_
  for Papertrail if you prefer using the CLI over their website
* Below are a few useful search queries:

================================================= ===========================
Description                                       Query
================================================= ===========================
All app output along with heroku routing requests ("app/web" OR "heroku/router")  -"newrelic"
All output minus Heroku stats                     -"newrelic.core.agent" or -"newrelic.core.data_collector" or -"sample#memory_total" or -"sample#load_avg_1m" or -"sample#active-connections"
Only web app output                               "app/web" -"newrelic"
Github API rate usage                             "core remaining:"
Heroku scheduled task output                      program:scheduler
Exceptions from Celery tasks                      CalledProcessError
Celery output worker                              -(dyno= OR exiting OR Booting OR Autorestarting OR State changed)
================================================= ===========================

2. `New Relic <https://elements.heroku.com/addons/newrelic>`_

* Excellent performance analysis tool

.. _celery_on_heroku:

--------------------------
Redis for background tasks
--------------------------

* Run `heroku addons:create heroku-redis:hobby-dev` to add the free Redis add-on
* This automatically sets up your `REDIS_URL` environment variable.
* Now run `heroku config --app <heroku_app_name>` to see the value of `REDIS_URL`
* Copy that value to a new environment variable on heroku and set it like this:
    * `heroku config:set CELERY_BROKER_URL=<REDIS_URL>`
* We don't set `CELERY_BROKER_URL` directly equal to `REDIS_URL` so that you're free to setup Celery with whatever broker you choose.

.. _redis_caching:

Adding Redis caching on Heroku
------------------------------

1. Determine if you want to use a
   `caching addon <https://elements.heroku.com/addons#caching>`_ or
   `redis addon <https://elements.heroku.com/addons#data-stores>`_.

   * This application has been tested with the `redis cloud addon <https://elements.heroku.com/addons/rediscloud>`_ for caching data from the Github API.
   * Redis was chosen for the following reasons:
        * Cache value larger than 1MB (for large articles)
        * Use the same service for other things later instead of just caching
2. Add your addon
    * `heroku addons:create rediscloud:30 --app <app_name>`
3. The application will automatically start caching if you used the redis cloud addon described above.  You can use a different Redis caching add-on, but you'll need to change the setup of the caching layer in `cache.py` appropriately.
4. See docs related to `using Python with redis on Heroku <https://devcenter.heroku.com/articles/rediscloud#using-redis-from-python>`_

.. _local_deployment:

Deploying with local instance
=============================

**Using this deployment method is only recommended for testing. However, often
times we've noticed this method is effective for testing locally and can be
faster than using `localhost` with your Github API callbacks.**

You can also 'deploy' the application running simply on `localhost` and expose
your `localhost` port through a secure tunnel using `ngrok <https://ngrok.com>`_.  Ngrok is recommended directly by Github for `testing Github webhooks <https://developer.github.com/webhooks/configuring/>`_.  It's
also useful if you have everything running locally and want to get quick
feedback from testers, etc. without having to setup Heroku or another hosting
machine.

1. Download `ngrok <https://ngrok.com>`_
2. Run locally using :ref:`one of the available methods <running_locally>`
3. Run ngrok and take note of the unique *Forwarding* URL
4. Set this base URL in your Github application as described in the
   :ref:`Github setup <github_registration>`

Now anyone can go to the ngrok URL and they'll get a secure tunnel to your
local machine for testing!

Setting Featured Guide
======================

By default, the featured guide is stored in an environment variable called
`FEATURED_GUIDE`.  This environment variable can be 1 of 2 types of values:

1. JSON-ified tuple of (title, stack)
2. String of title

Version 1 is more *correct* since guides can have duplicate titles but not
duplicate titles **and** stack.  However, it's easier to use version 2 because
it's a simple string.  Therefore, you can use whichever suits your situation,
if you don't think you'll have duplicate titles then version 2 is preferred.

--------------------------
Using environment variable
--------------------------

This environment variable must be set in a way that will persist across all
running instances of the application. You can do this with the Heroku CLI or
admin panel, if you're running on Heroku.

-----------
Using Redis
-----------

A better solution for managing the featured guide is to use Redis.  The CMS
will automatically use a single key in the 'caching' Redis database mentioned
above if you're using the `REDISCLOUD_URL` setup.  So, there's no need to worry
about this if you are using the standard caching setup with `REDISCLOUD_URL`.

The CMS will automatically use version 1 of the `FEATURED_GUIDE` variable when
using Redis so you don't have to worry about duplicate titles.

**You will not be able to set the featured guide via the CMS UI if you're not
using Redis to store the featured guide.**  This is because setting an
environment variable via the application itself is unreliable if you're running
multiple instances of the application on multiple dynos or servers.

