# Pluralsight KnowledgeBase

The Pluralsight knowledgebase is a community-based website to help Software
Developers learn new skills through writing and editing technical writing.

## Requirements

- Programming lanuage: [Python](http://python.org) 2.7.3 - Python 2.7.9
- Web framework: [Flask](http://flask.pocoo.org)
- HTTP server: [Gunicorn](http://gunicorn.org)

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

### Run application locally

1. Run `python app.py`
2. Browse to URL mentioned at prompt

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
    - `git remote add heroku git@heroku.com:<name>.git where <name> is the name
      of your heroku app from step 1.
3. Deploy changes
    -`git push heroku master`
    - **Make sure your changes are committed locally first!**
