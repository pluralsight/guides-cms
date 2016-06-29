============
Requirements
============

* Programming lanuage: `Python 2.7.10 <http://python.org>`_
* Web framework: `Flask <http://flask.pocoo.org>`_
* HTTP server: `Gunicorn <http://gunicorn.org>`_
* See requirements.txt for additional Python package requirements
* Background jobs: `Redis <http://redis.io>`_

---------------------
Optional requirements
---------------------

* Caching: `Redis <http://redis.io>`_

=============================
Install for local development
=============================

1. Clone repo
    * `git clone <repo> <location_to_clone>`
2. Install `virtualenv <https://pypi.python.org/pypi/virtualenv>`_
3. Create virtual environment for project
    * `virtualenv <env>` where <env> is location to where you want to store
      project environment.  <env> is typically the directory of your git repo
      or something like `~/.virtualenvs/env_name`.
4. Activate virtualenv
    * `source <path_to_env>/bin/activate`
5. Install requirements
    * `pip install -r requirements.txt`
6. Setup :doc:`Github application <github_setup>`

---------------------------
Setup environment variables
---------------------------

1. Copy example_config.py to config.py and populate config.DevelopmentConfig with your own data.
    * This is where you'll copy and paste your Github OAuth application's credentials.
    * The defaults are all set in the config.Config so override only values you need.  The following are required:
        * SECRET_KEY
        * GITHUB_CLIENT_ID
        * GITHUB_SECRET
        * REPO_OWNER - Name of your github user
        * REPO_NAME - Name of repository you'll store the guide content
        * REPO_OWNER_ACCESS_TOKEN - OAuth token of your github user or owner of the repository where the guide content is stored. You cannot set this until after you run the application locally and authorize it with your github account as described below.
        * CELERY_BROKER_URL - URL of Redis (or another broker) for handling background jobs (see :ref:`instructions for Celery on heroku <celery_on_heroku>` for help).
        * DOMAIN - Base URL where your site will be running. This can be the URL of your Heroku deployment or localhost like `127.0.0.1:5000` or `0.0.0.0:5000`.

.. _first_time_setup:

----------------
First-time Setup
----------------

1. Run `python run.py` or `make run_flask` if you have Make installed
2. Browse to `http://127.0.0.1:5000/login/`
3. Login with your github account and authorize your newly created application
    * **Login with the account you set as the REPO_OWNER**
4. Check your logs for the new token printed. This will be a CRTICAL level log message.
5. You'll need to place that token in the `REPO_OWNER_ACCESS_TOKEN` environment variable.
6. Shutdown the local flask webserver with `Ctrl-C` and run `python run.py` again

Now you can :ref:`test things from the CLI <wo_browser>` if that's more your speed. However, there's one more step to setting up the ability to publish articles.  This requires :ref:`running a celery process for background jobs <celery_setup>`.

You can try creating a guide once you have celery running locally or your `CELERY_BROKER_URL` configured to a running Redis server.

Note now you *can* use this local server and :ref:`expose it to the Internet
through a secure tunnel <local_deployment>` if you want!

.. _running_locally:

--------------------------------
Run locally with Flask webserver
--------------------------------

1. Follow the :ref:`first-time setup instructions <first_time_setup>`
2.  Run `python run.py` or `make run_flask` and use `Ctrl-C` to stop the server.

-----------------------------------
Run locally with Gunicorn webserver
-----------------------------------

1. Follow the :ref:`first-time setup instructions <first_time_setup>`
2. Run `make run_gunicorn`

.. _celery_setup:

-------------------------------------------
Setting up Celery for background processing
-------------------------------------------

You already have `Celery <http://celeryproject.org>`_ installed if you used the requirements.txt file.  However, now you need `Redis <http://redis.io>`_ running to process background jobs from Celery and fully enable publishing articles.

Setting up Redis locally is outside the scope of this document.  You can refer
to the `Redis documentation <http://redis.io/documentation>`_ for that.
However, you can easily setup Redis on `Heroku <http://heroku.com>`_ by
following the :ref:`these instructions <celery_on_heroku>`.
