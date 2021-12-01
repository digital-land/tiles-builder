[![Build and deploy tile server](https://github.com/digital-land/tiles-builder/actions/workflows/build.yml/badge.svg)](https://github.com/digital-land/tiles-builder/actions/workflows/build.yml)

# Tiles Builder
Builds the digital-land vector tiles databases from collected geometries. The application is built into a 
docker image containing datasette with a baked in sqlite database with spatialite extensions.

The docker image is kept in dockerhub and deployed to AWS Elasticbeanstalk.


Getting started
---------------

To initialise environment

    make makerules
    make init
    
To generate the vector tilesets

    make build
    
To generate a datasette docker image packaged with the vector tilesets

    make build-docker
    
To push and deploy the image

    make push


## Github action - Build & Deployment

The action runs daily to submit an AWS batch job to rebuild the docker image by cloning this repository and running
the default make target.

The steps taken by the default make target are:

1. Downloads the entity.sqlite3 db from the collection-dataset S3 bucket (key = /entity-builder/dataset/entity.sqlite3)

2. Installs tipicanoe

3. Runs [build_tiles.py ](build_tiles.py ) on the entity db to build the tiles.

4. Builds and pushes docker image containing datasette and db

5. Updates Elasticbeanstalk environment


The application is running in Elasticbeanstalk in the digital land AWS dev account.

1. Application name: Datasette-tile-server-v2

2. Environment: Datasettetileserverv2-env

The docker image is built and pushed to dockerhub [https://hub.docker.com/r/digitalland/tile_v2_digital_land](https://hub.docker.com/r/digitalland/tile_v2_digital_land)

The Elasticbeanstalk application uses this run configuration [Dockerrun.aws.json](Dockerrun.aws.json)


# Licence

The software in this project is open source and covered by the [LICENSE](LICENSE) file.

Individual datasets copied into this repository may have specific copyright and licensing, otherwise all content and data in this repository is [© Crown copyright](http://www.nationalarchives.gov.uk/information-management/re-using-public-sector-information/copyright-and-re-use/crown-copyright/) and available under the terms of the [Open Government 3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) licence.
