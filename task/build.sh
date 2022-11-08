#!/usr/bin/env bash

# TODO: replace with aws cli call to S3 download
curl -o entity.sqlite https://files.temporary.digital-land.info/entity-builder/dataset/entity.sqlite3

python3 build_tiles.py --entity-path entity.sqlite --output-dir /mnt/tiles

date > /mnt/tiles/updated
