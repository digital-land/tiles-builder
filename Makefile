include makerules/makerules.mk

BUILD_TAG_TILE := digitalland/tile_v2
CACHE_DIR := var/cache/
ENTITY_DB := var/cache/entity.sqlite3
TILE_CONFIG_DIR := config/


all:: $(ENTITY_DB) build build-docker

build: tippecanoe-check
	python3 build_tiles.py --entity-path $(ENTITY_DB) --output-dir $(CACHE_DIR)

build-docker: docker-check $(ENTITY_DB)
	digital-land build-datasette --data-dir $(CACHE_DIR) --ext "mbtiles" --tag $(BUILD_TAG_TILE) --options "-m $(TILE_CONFIG_DIR)metadata.json,--install=datasette-cors,--install=datasette-tiles,--plugins-dir=$(TILE_CONFIG_DIR)plugins/"

push: docker-check
	echo $DOCKER_TOKEN | docker login --username digitalland --password-stdin
	docker push $(BUILD_TAG_TILE)_digital_land
	aws elasticbeanstalk update-environment --application-name Datasette-tile-server-v2 --environment-name Datasettetileserverv2-env --version-label datasette-tile-server-v2-source


lint: black-check flake8

black-check:
	black --check  . --exclude '/(src|\.venv/)'

flake8:
	flake8 --exclude 'src,.venv' .

clobber::
	rm -rf $(CACHE_DIR)

docker-check:
ifeq (, $(shell which docker))
	$(error "No docker in $(PATH), consider doing apt-get install docker OR brew install --cask docker")
endif

tippecanoe-check:
ifeq (, $(shell which tippecanoe))
	git clone https://github.com/mapbox/tippecanoe.git
	cd tippecanoe
	make -j
	make install
	cd ..
endif

#  entity index
$(ENTITY_DB):
	@mkdir -p $(CACHE_DIR)
	curl -qfsL 'https://collection-dataset.s3.eu-west-2.amazonaws.com/entity-builder/dataset/entity.sqlite3' > $@
