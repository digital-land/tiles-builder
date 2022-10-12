# TODO add this ECR repository to terraform
BUILD_TAG := 955696714113.dkr.ecr.eu-west-2.amazonaws.com/tile_v2_digital_land
CACHE_DIR := var/cache/
ENTITY_DB := var/cache/entity.sqlite3
CONFIG_DIR := config/

ifeq ($(ENVIRONMENT),)
ENVIRONMENT=production
endif
ifeq ($(COLLECTION_DATASET_BUCKET_NAME),)
COLLECTION_DATASET_BUCKET_NAME=digital-land-$(ENVIRONMENT)-collection-dataset
endif

all:: $(ENTITY_DB) build build-docker

init::
	sudo apt-get update && sudo apt-get -y install libsqlite3-dev zlib1g-dev
	pip3 install --upgrade -r requirements.txt

tippecanoe: init
	./build_tippecanoe.sh

build: tippecanoe
	python3 build_tiles.py --entity-path $(ENTITY_DB) --output-dir $(CACHE_DIR)

build-docker: docker-check $(ENTITY_DB)
	datasette package --port 5000 --extra-options="--setting sql_time_limit_ms 8000" --spatialite -m $(CONFIG_DIR)metadata.json --install=datasette-cors --install=datasette-tiles --plugins-dir=$(CONFIG_DIR)plugins/ $(CACHE_DIR)*.mbtiles --tag $(BUILD_TAG):temp
	docker build -t $(BUILD_TAG):latest --build-arg APP_IMAGE=$(BUILD_TAG):temp .

login-docker:
	aws ecr-public get-login-password --region us-east-1 | docker login --username AWS --password-stdin public.ecr.aws/t4s4p5s3

push: docker-check login-docker
	docker push $(BUILD_TAG):latest
	aws elasticbeanstalk update-environment --application-name Datasette-tile-server-v2 --environment-name Datasettetileserverv2-env --version-label datasette-tile-server-v2-source-configuration-2

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

# entity database
$(ENTITY_DB):
	@mkdir -p $(CACHE_DIR)
	curl -qfsL 'https://$(COLLECTION_DATASET_BUCKET_NAME).s3.eu-west-2.amazonaws.com/entity-builder/dataset/entity.sqlite3' > $@
