.PHONY: start init

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