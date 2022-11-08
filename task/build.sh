#!/usr/bin/env bash

echo "$EVENT_ID: task running with env vars S3_BUCKET = $S3_BUCKET and S3_KEY = $S3_KEY"

DATABASE=${S3_KEY##*/}
DATABASE_NAME=${DATABASE%.*}

if ! [ -f $DATABASE_NAME.sqlite3 ]; then
  echo "$EVENT_ID: attempting download from $COLLECTION_DATA_URL/$S3_KEY"
  if [[ $(curl -sI $COLLECTION_DATA_URL/$S3_KEY | grep "200 OK") == *200* ]]; then
    curl -sO $COLLECTION_DATA_URL/$S3_KEY || echo "$EVENT_ID: failed to download from $COLLECTION_DATA_URL/$S3_KEY"
  else
    echo "$EVENT_ID: failed to download from $COLLECTION_DATA_URL/$S3_KEY"
  fi
  echo "$EVENT_ID: finished downloading from $COLLECTION_DATA_URL/$S3_KEY"
else
  echo "$EVENT_ID: did not need to download files"
fi

mkdir -p /mnt/tiles/temporary
echo "$EVENT_ID: building tiles"
python3 build_tiles.py --entity-path entity.sqlite3 --output-dir /mnt/tiles/temporary && echo "$EVENT_ID: tiles built successfully"
echo "$EVENT_ID: finished building tiles"
rm -rf /mnt/tiles/*.mbtiles
rm -rf /mnt/tiles/*.geojson

mv /mnt/tiles/temporary/* /mnt/tiles
rm -rf /mnt/tiles/temporary

echo "$EVENT_ID: tile files swapped out"
date > /mnt/tiles/updated
