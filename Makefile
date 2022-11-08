.PHONY: start init

./files/entity.sqlite3:
	@mkdir -p ./files
	@curl -o ./files/entity.sqlite3 https://files.temporary.digital-land.info/entity-builder/dataset/entity.sqlite3

./files/tiles:
	@mkdir -p ./files/tiles
	@cd task && docker-compose up --build

init: ./files/datasets ./files/tiles

start: init
	@cd application && docker-compose up --build
