# Database setup

Currently the database is not used in this project.  It most likely will be
used in the future, but for the MVP we're foregoing any local storage and
utilizing only github.

## Setting up database locally

1. Make sure you have Postgres running
2. Create a new database called 'pskb_dev'
3. Initialize migration setup
    - `./manage.py db init`
4. Create first migration
    - `./manage.py db migrate`
5. Apply the first migration
    - `./manage.py db upgrade`

## Setting up database on heroku

1. Add small (free) db to your app
    - `heroku addons:create heroku-postgresql:hobby-dev --app <app_name>`
2. Run migration on heroku
    - `heroku run python manage.py db upgrade --app <app_name>`

### Interacting with database locally

[Flask-SQLAlchemy](http://pythonhosted.org/Flask-SQLAlchemy/index.html) is used
to interface with the [Postgres](http://www.postgresql.org) database.  This
layer sits on top of [SQLAlchemy](http://www.sqlalchemy.org) to provide a nicer
API to the database.

You can test out the database without a browser by running the following
command, provided by
[Flask-Migrate](http://flask-migrate.readthedocs.org/en/latest/):
    - `python migrate.py db shell`

### Interacting with database remotely

- Run `heroku config --app <app_name>` and take note of your DATABASE_URL
- Run `psql <DATABASE_URL>`

#### Database migrations

Database migrations are handled by [Flask-Migrate](http://flask-migrate.readthedocs.org/en/latest/).  This Flask extension manages some of the lower-level work with
[alembic](https://alembic.readthedocs.org/en/latest/index.html), which does the
real migration work.

The existing migrations can be found in the migrations folder.

#### Creating a database migration

1. Apply changes to models.py
2. Run `python manage.py db migrate` to creation the new migration script
3. Double-check the migration script the above command generated.
    - The file will exist somewhere in migrations/versions/.  The migrate
      command should point you there.
4. Once the migration script is ready, run `python manage.py db upgrade`
5. Add new migrations files to git

##### Psql tips

- Use \dt to list tables
- Use \? to get help on shortcut commands
