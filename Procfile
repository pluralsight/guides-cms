web: newrelic-admin run-program gunicorn -w 6 -k gevent --worker-connections 512 --max-requests 1000 pskb_website:app
worker: newrelic-admin run-program celery worker --app=pskb_website.tasks.celery
