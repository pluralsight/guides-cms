============
Requirements
============

* Programming lanuage: `Python 2.7.10 <http://python.org>`_
* Web framework: `Flask <http://flask.pocoo.org>`_
* HTTP server: `Gunicorn <http://gunicorn.org>`_
* See requirements.txt for additional Python package requirements

---------------------
Optional requirements
---------------------

* Caching: [Redis](http://redis.io)

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

1. Copy example_config.py to config.py and populate config.DevelopmentConfig
    with your own data.
    * This is where you'll copy and paste your Github OAuth application's
      credentials.
2. Head over to the views.py file on [this specific line](https://github.com/pluralsight/guides-cms/blob/master/pskb_website/views.py#L175) and uncomment it.
    * Really need a better way to do this. Any ideas? Send us a Pull Request!

--------------------------------
Run locally with Flask webserver
--------------------------------

1. Run `python run.py`
2. Browse to URL mentioned at prompt
3. Click the Signin with github and authenticate the application
4. Check your logs for the token printed by the code change above.
5. You'll need to place that token in the `REPO_OWNER` environment variable.

Now you should be setup and ready, but you can even test things from the CLI if
that's more your speed.

-----------------------
Testing without browser
-----------------------

You can test a lot of the functionality of the application without a web
browser.  In general, much of the interaction with the Github API can be used
directly from the command-line.  To do this run the following:

`python manage.py shell`

Now you have access to the entire application.  To test a Github API response
try the following::

    from pskb_website import remote
    remote.read_user_from_github(username='octocat')

You should now see the description of the famous Github octocat user!
