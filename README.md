# Hacker Guides

[hack.guides](http://tutorials.pluralsight.com) is a community-based website to
help Software Developers learn new skills through writing and editing technical
writing.

## Main requirements

- Programming lanuage: [Python](http://python.org) 2.7.3 - Python 2.7.10
- Web framework: [Flask](http://flask.pocoo.org)
- HTTP server: [Gunicorn](http://gunicorn.org)

## Optional requirements

These are not currently required, but they maybe in the future.

- Database server: [Postgres](http://www.postgresql.org)
- Python ORM: [SQLAlchemy](http://www.sqlalchemy.org)
- Documentation: [Sphinx](http://sphinx-doc.org)
    - Required for building documentation locally with `make html_docs` command
- Caching: [Redis](http://redis.io)
    - Requires redis module, install with: `pip install redis`

## Install for development

1. Clone repo:
    - `git clone <repo> <location_to_clone>`
2. Install [virtualenv](https://pypi.python.org/pypi/virtualenv)
3. Create virtual environment for project:
    - `virtualenv <env>` where <env> is location to where you want to store
      project environment.  <env> is typically the directory of your git repo
      or something like `~/.virtualenvs/env_name`.
4. Activate virtualenv:
    - `source <path_to_env>/bin/activate`
5. Install requirements:
    - `pip install -r requirements.txt`

### Run application locally with built-in flask webserver

1. Copy example_config.py to config.py and populate config.DevelopmentConfig
   with your own data.
2. Run `./run.py`
3. Browse to URL mentioned at prompt

### Run application locally with heroku Procfile

You'll need to complete the setup below for getting things running on heroku
before doing this, or at least setting up your heroku environment variables as
described below.  Then:

1. Run `heroku config --app <app_name>` to see all the configuration
2. Copy all the these configuration values into a file with the `key=value` format instead of `key:value` which is the output of the heroku command.
3. Run `heroku local --env <file_from_step_2>`

### Run application on heroku

Heroku has a [good guide for Python apps](https://devcenter.heroku.com/articles/getting-started-with-python#introduction)
that gives a nice overview of the concepts you'll need to know to get going,
but some of the specifics for this setup are slightly different.

[Real Python](https://realpython.com) also has a [great guide on setting up a
basic flask app on heroku](https://realpython.com/blog/python/flask-by-example-part-1-project-setup/).

The following steps assume you have the basic [heroku toolbelt installed](https://devcenter.heroku.com/articles/getting-started-with-python#set-up).

1. Create [heroku](http://heroku.com) app
    - `heroku create [name]`
    - You can specify a name but it must be unique. You can also leave it blank
      and Heroku will create a unique name for you.
2. Add git remote for your app
    - `git remote add heroku git@heroku.com:<name>.git` where <name> is the name
      of your heroku app from step 1.
3. Setup heroku config
    - See example_config.py for a listing of the environment variables that
      must be setup in your heroku config.
    - You can set heroku config variables with the following syntax:
        - `heroku config:set APP_SETTINGS=config.ProductionConfig`
        - ... (see example_config.py for full list)
        - Or something like the following if you have multiple remotes for heroku
        - `heroku config:set APP_SETTINGS=config.ProductionConfig --app pro`
        - `heroku config:set APP_SETTINGS=config.StagingConfig --app stage`
        - ... (see example_config.py for full list)
4. Deploy changes
    - `git push heroku master`
    - Or something like the following if you have multiple remotes for heroku
    - `git push stage master` where <stage> is remote name for heroku and
      master is local branch you want to push.
    - **Make sure your changes are committed locally first!**

By default the application will be served up by [Gunicorn](http://gunicorn.org)
only.  This is great for testing, but gunicorn is best when run behind a proxy
like [nginx](http://nginx.org). Gunicorn is easily suseptible to
[DOS](https://en.wikipedia.org/wiki/Denial-of-service_attack) issues.  You can
slightly improve your performance on heroku by using setting the
`WEB_CONCURRENCY` environment variable, which gunicorn automatically honors:
    - `heroku config:set WEB_CONCURRENCY=3`

You'll want to set this to something suitable for the size of your
[heroku dyno](https://www.heroku.com/pricing) and the memory requirements of
your the flask application.

#### Heroku add-ons worth checking out

1. [Papertrail](https://elements.heroku.com/addons/papertrail)
    - Provides bigger log for debugging issues and enables easy searching

#### Testing without browser

1. `pip install Flask-Migrate`

You can test a lot of the functionality of the application without a web
browser.  In general, much of the interaction with the Github API can be used
directly from the command-line.  To do this run the following

- `python manage.py shell`

Now you have access to all the application.  So, to test a Github API response
try the following:

- `from pskb_website import remote`
- `remote.read_user_from_github(username='octocat')`

#### Making changes to Javascript

You can find the Javascript code in the `pskb_website/static/js/vendor/`
directory.  The full verison and minified versions are kept in source control
so they can be easily modified and re-minified.  To do this you'll need to
install a Javascript minifier.  We recommend using [UglifyJS](https://github.com/mishoo/UglifyJS) which can be easily installed with [npm](https://www.npmjs.com).

Once you have a minifier installed, you can make changes to the 'full source'
of the Javascript then minify it with something simliar to the following
(depending on your minifier):
    - `uglifyjs <full_source> > <new_minified_source>`


#### Adding Redis caching on Heroku

1. Determine if you want to use a
   [caching addon](https://elements.heroku.com/addons#caching) or
   [redis addon](https://elements.heroku.com/addons#data-stores).

   - This application has been tested with the [redis cloud addon](https://elements.heroku.com/addons/rediscloud).
   - Redis was chosen for the following reasons:
    - Cache value larger than 1MB (for large articles)
    - Use the same service for other things later instead of just caching
2. Add your addon
    - `heroku addons:create rediscloud:30 --app <app_name>`
3. See [heroku python with redis docs](https://devcenter.heroku.com/articles/rediscloud#using-redis-from-python)
