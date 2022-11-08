.PHONY: start init

./files/datasets:
	@mkdir -p ./files/datasets
	@curl -o ./files/datasets/entity.sqlite https://files.temporary.digital-land.info/entity-builder/dataset/entity.sqlite3

./files/tiles:
	@mkdir -p ./files/tiles
	@cd task && docker-compose up --build

init: ./files/datasets ./files/tiles

start: init
	@cd application && docker-compose up --build
