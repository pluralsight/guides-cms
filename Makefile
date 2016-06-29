# Local tasks

VENV=env

error_check:
	pylint -E `find ./pskb_website -iname '*.py' -o -path ./migrations -prune`

full_lint:
	pylint --disable=bad-continuation `find ./pskb_website -iname '*.py' -o -path ./migrations -prune`

clean:
	@find . -name "*.pyc" -delete
	@find . -name "__pycache__" -delete

bootstrap: clean
	@virtualenv $(VENV) -p python2.7
	@$(VENV)/bin/pip install -r requirements.txt
	@test -e config.py || cp -n example_config.py config.py
	@echo "\nPlease, update your \033[0;34m./config.py\033[0m file to move forward, then you can execute \033[0;34mmake run\033[0m"

run:
	$(VENV)/bin/python run.py

test:
	$(VENV)/bin/py.test pskb_website

html_docs:
	cd docs; make html

# Remote servers tasks

deploy_stage:
	git push stage master

deploy_prod:
	git push prod master

push:
	git push origin master

stage_logs:
	heroku logs -t --app pskb-stage

prod_logs:
	heroku logs -t --app pskb-prod

prod_logs_app:
	heroku logs -t --app pskb-prod --source app

run_flask:
	python run.py

run_gunicorn:
	export APP_SETTINGS=config.DevelopmentConfig && gunicorn -w 6 -k gevent --worker-connections 512 --max-requests 1000 pskb_website:app -b 127.0.0.1:5000
