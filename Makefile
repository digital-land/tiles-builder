include makerules/makerules.mk

# TODO add this ECR repository to terraform
BUILD_TAG_TILE := 955696714113.dkr.ecr.eu-west-2.amazonaws.com/tile_v2
# If you're wondering where this suffix comes from: https://github.com/digital-land/digital-land-python/blob/c114044bd4210d19850b97b15ea562348010eb54/digital_land/datasette/docker.py#L26
PUSH_TAG_TILE := $(BUILD_TAG_TILE)_digital_land
CACHE_DIR := var/cache/
ENTITY_DB := var/cache/entity.sqlite3
TILE_CONFIG_DIR := config/

ifeq ($(ENVIRONMENT),)
ENVIRONMENT=production
endif
ifeq ($(COLLECTION_DATASET_BUCKET_NAME),)
COLLECTION_DATASET_BUCKET_NAME=digital-land-$(ENVIRONMENT)-collection-dataset
endif

all:: $(ENTITY_DB) build build-docker

build: tippecanoe-check
	python3 build_tiles.py --entity-path $(ENTITY_DB) --output-dir $(CACHE_DIR)

build-docker: docker-check $(ENTITY_DB)
	digital-land build-datasette --data-dir $(CACHE_DIR) --ext "mbtiles" --tag $(BUILD_TAG_TILE) --options "-m $(TILE_CONFIG_DIR)metadata.json,--install=datasette-cors,--install=datasette-tiles,--plugins-dir=$(TILE_CONFIG_DIR)plugins/"

login-docker:
	aws ecr get-login-password --region eu-west-2 | docker login --username AWS --password-stdin 955696714113.dkr.ecr.eu-west-2.amazonaws.com

push: docker-check login-docker
	docker push $(PUSH_TAG_TILE)
	aws elasticbeanstalk update-environment --application-name Datasette-tile-server-v2 --environment-name Datasettetileserverv2-env --version-label datasette-tile-server-v2-source-configuration-2

lint: black-check flake8

black-check:
	black --check  . --exclude '/(src|\.venv/)'

flake8:
	flake8 --exclude 'src,.venv' .

clobber::
	rm -rf $(CACHE_DIR)

aws-build::
	aws batch submit-job --job-name tiles-build-$(shell date '+%Y-%m-%d-%H-%M-%S') --job-queue dl-batch-queue --job-definition dl-batch-def --container-overrides '{"environment": [{"name":"BATCH_FILE_URL","value":"https://raw.githubusercontent.com/digital-land/docker-builds/main/builder_run.sh"}, {"name" : "REPOSITORY","value" : "tiles-builder"}]}'

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
	curl -qfsL 'https://$(COLLECTION_DATASET_BUCKET_NAME).s3.eu-west-2.amazonaws.com/entity-builder/dataset/entity.sqlite3' > $@
