#!/usr/bin/env bash

echo "running locally"

# make temporary directory for running locally
mkdir -p temp/entity
mkdir -p temp/tiles

# download entity.sqlite3
if ! [ -f "temp/entity/entity.sqlite3" ]; then
  echo "Downloading entity.sqlite3"
  curl "https://files.planning.data.gov.uk/entity-builder/dataset/entity.sqlite3" > "temp/entity/entity.sqlite3"
fi

# run python code to extract files
echo "$EVENT_ID: building tiles"
python3 build_tiles.py --entity-path temp/entity/entity.sqlite3 --output-dir temp/tiles
echo "$EVENT_ID: finished building tiles"



