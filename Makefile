.PHONY: application task test

./files:
	@mkdir -p ./files/tiles
	cd task && UID=$${UID} \
			   GID=$${GID} \
			   AWS_ACCESS_KEY_ID="$$AWS_ACCESS_KEY_ID" \
			   AWS_SECRET_ACCESS_KEY="$$AWS_SECRET_ACCESS_KEY" \
			   AWS_SESSION_TOKEN="$$AWS_SESSION_TOKEN" \
			   AWS_SECURITY_TOKEN="$$AWS_SECURITY_TOKEN" \
			   AWS_SESSION_EXPIRATION="$$AWS_SESSION_EXPIRATION" \
			   docker-compose up --build

task: ./files

application: task
	@cd application && docker-compose up --build

clean:
	@rm -rf ./files


test-integration:
	python -m pytest --cov=task tests/integration

test-e2e:
	python -m pytest --cov=task tests/e2e

test: test-integration test-e2e

lint:
	black .
	flake8 .

init:
	python -m pip install pip-tools
	python -m piptools sync task/dev-requirements.txt task/requirements.txt
	python -m pre_commit install
