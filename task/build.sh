#!/usr/bin/env bash

DATABASE=${S3_KEY##*/}
DATABASE_NAME=${DATABASE%.*}

echo "$EVENT_ID: running with settings: S3_BUCKET=$S3_BUCKET, S3_KEY=$S3_KEY, DATABASE=$DATABASE, DATABASE_NAME=$DATABASE_NAME"

if [[ $DATABASE_NAME == "entity" ]] || [[ $DATABASE_NAME == "digital-land" ]]; then
  echo "$EVENT_ID: wrong database, skipping"
  exit 1
fi

echo "$EVENT_ID: checking lock"

if [ -f "/mnt/tiles/lock-$DATABASE_NAME" ]; then
  if [[ "$(echo "$(date +%s) - $(cat "/mnt/tiles/lock-$DATABASE_NAME") - 300" | bc)" -ge "0" ]]; then
    echo "$EVENT_ID: lock-$DATABASE_NAME exists ($(cat "/mnt/tiles/lock-$DATABASE_NAME")) but is stale, resetting"
  else
    echo "$EVENT_ID: lock-$DATABASE_NAME exists ($(cat "/mnt/tiles/lock-$DATABASE_NAME")) and is not stale, exiting"
    exit 1
  fi
else
  echo "$EVENT_ID: no current lock-$DATABASE_NAME"
  date +%s >"/mnt/tiles/lock-$DATABASE_NAME"
fi

echo "$EVENT_ID: removing existing temporary tiles"
rm -rf /mnt/tiles/temporary/$DATABASE_NAME/

if ! [ -f "$DATABASE_NAME.sqlite3" ]; then
  echo "$EVENT_ID: attempting download from s3://$S3_BUCKET/$S3_KEY"
  aws s3api get-object --bucket "$S3_BUCKET" --key "$S3_KEY" "$DATABASE_NAME.sqlite3" >/dev/null

  if ! [ -f "$DATABASE_NAME.sqlite3" ]; then
    echo "$EVENT_ID: failed to download from s3://$S3_BUCKET/$S3_KEY"
    exit 1
  else
    echo "$EVENT_ID: finished downloading from s3://$S3_BUCKET/$S3_KEY"
  fi
else
  echo "$EVENT_ID: did not need to download files"
fi

mkdir -p /mnt/tiles/temporary/$DATABASE_NAME
echo "$EVENT_ID: building tiles"
PYTHON_OUTPUT=$(python3 build_tiles.py --entity-path $DATABASE_NAME.sqlite3 --output-dir /mnt/tiles/temporary/$DATABASE_NAME --hash-dir /mnt/tiles/dataset/hashes)

# Check if the Python script indicates that tiles were built successfully
if echo "$PYTHON_OUTPUT" | grep -q "Tiles built successfully*"; then
  echo "$EVENT_ID: finished building tiles"
  rm -rf /mnt/tiles/$DATABASE_NAME.mbtiles
  rm -rf /mnt/tiles/$DATABASE_NAME.geojson

  mv /mnt/tiles/temporary/$DATABASE_NAME/* /mnt/tiles
  rm -rf /mnt/tiles/temporary/$DATABASE_NAME

  echo "$EVENT_ID: tile files swapped out"
  date +%s >/mnt/tiles/updated
  rm "/mnt/tiles/lock-$DATABASE_NAME"
else
  echo "Dataset already exist with same hash"
  echo "$PYTHON_OUTPUT"
fi
