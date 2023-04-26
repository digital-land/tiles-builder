#!/usr/bin/env bash

echo "running locally"

# make temporary directory for running locally
mkdir -p files/entity
mkdir -p files/tiles

# download entity.sqlite3
if ! [ -f "temp/entity/entity.sqlite3" ]; then
  echo "Downloading entity.sqlite3"
  curl "https://files.planning.data.gov.uk/entity-builder/dataset/entity.sqlite3" > "files/entity/entity.sqlite3"
fi

# run python code to extract files
echo "$EVENT_ID: building tiles"
python3 build_tiles.py --entity-path files/entity/entity.sqlite3 --output-dir files/tiles
echo "$EVENT_ID: finished building tiles"



