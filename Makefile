error_check:
	pylint -E `find . -iname '*.py' -o -path ./migrations -prune`

full_lint:
	pylint --disable=bad-continuation `find . -iname '*.py' -o -path ./migrations -prune`

clean:
	find . -name "*.pyc" -delete
	find . -name "__pycache__" -delete

deploy_stage:
	git push stage master

push:
	git push origin master

stage_logs:
	heroku logs -t --app pskb-stage

html_docs:
	cd docs; make html
