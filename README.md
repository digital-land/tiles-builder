[![Tile Server](https://github.com/digital-land/tiles-builder/actions/workflows/deploy-application.yml/badge.svg)](https://github.com/digital-land/tiles-builder/actions/workflows/deploy-application.yml)
[![Tile Builder](https://github.com/digital-land/tiles-builder/actions/workflows/deploy-task.yml/badge.svg)](https://github.com/digital-land/tiles-builder/actions/workflows/deploy-task.yml)

# Tiles Server

The tiles server consists of two separate deployable images: the server itself and the tile builder task.

## Running locally

To run the service locally run `make application` while authenticated with `aws-vault`. It is advised that you limit the
number of other tasks running and have a minimum of 6GB free space for the required files.

To reset the current tiles stored, run `make clean` before running `make application` to start from a clean slate.

## Building & Deployment

There are two separate GitHub actions [`deploy-application.yml`](.github/workflows/deploy-application.yml) and 
[`deploy-task.yml`](.github/workflows/deploy-task.yml). Each will run when changes are made to their respective
code directories `./application` and `./task`.

# Licence

The software in this project is open source and covered by the [LICENSE](LICENSE) file.

Individual datasets copied into this repository may have specific copyright and licensing, otherwise all content and 
data in this repository is [© Crown copyright](http://www.nationalarchives.gov.uk/information-management/re-using-public-sector-information/copyright-and-re-use/crown-copyright/) 
and available under the terms of the [Open Government 3.0](https://www.nationalarchives.gov.uk/doc/open-government-licence/version/3/) licence.
