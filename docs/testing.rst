=======
Testing
=======

.. _wo_browser:

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

.. _adding_tests:

------------
Adding tests
------------
New tests can be added under a **test** directory in the appropriate package.
The convention right now is to name the file as **test_*.py**

.. _running_tests:

---------------------
Running tests locally
---------------------

To run tests locally, execute the following command from project root:

`python py.test`

This will find and run all tests in the current working directory.
