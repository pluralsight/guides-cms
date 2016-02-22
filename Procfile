web: gunicorn -w 6 -k gevent --worker-connections 512 --max-requests 1000 pskb_website:app
worker: celery worker --app=pskb_website.tasks.celery
