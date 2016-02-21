web: gunicorn -w 4 -k gevent --worker-connections 256 --max-requests 256 pskb_website:app
worker: celery worker --app=pskb_website.tasks.celery
