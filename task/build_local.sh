#!/usr/bin/env bash

echo "running locally"

# # make temporary directory for running locally
mkdir -p files/sqlites
mkdir -p files/tiles

# download entity.sqlite3
if ! [ -f "files/sqlites/flood-risk-zone.sqlite3" ]; then
  echo "Downloading entity.sqlite3"
  curl "https://files.planning.data.gov.uk/flood-risk-zone-collection/dataset/flood-risk-zone.sqlite3" > "files/sqlites/flood-risk-zone.sqlite3"
fi

# run python code to extract files
echo "$EVENT_ID: building tiles"
python3 build_tiles.py --entity-path files/sqlites/flood-risk-zone.sqlite3 --output-dir files/tiles
echo "$EVENT_ID: finished building tiles"
