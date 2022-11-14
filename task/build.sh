#!/usr/bin/env bash

echo "$EVENT_ID: task running with env vars S3_BUCKET = $S3_BUCKET and S3_KEY = $S3_KEY"

DATABASE=${S3_KEY##*/}
DATABASE_NAME=${DATABASE%.*}

if [[ $DATABASE_NAME != "entity" ]]; then
  echo "$EVENT_ID: wrong database, skipping"
  exit 1
fi

echo "$EVENT_ID: checking lock"
if [ -f /mnt/tiles/lock ]; then
  echo "$EVENT_ID: lock exists ($(cat /mnt/tiles/lock)) backing off"
  exit 1
else
  echo "$EVENT_ID: no current lock"
  date > /mnt/tiles/lock
fi

if ! [ -f $DATABASE_NAME.sqlite3 ]; then
  echo "$EVENT_ID: attempting download from s3://$S3_BUCKET/$S3_KEY"
  aws s3api get-object --bucket $S3_BUCKET --key $S3_KEYS $DATABASE_NAME.sqlite3 || \
    echo "$EVENT_ID: failed to download from s3://$S3_BUCKET/$S3_KEY" && exit 1

  echo "$EVENT_ID: finished downloading from s3://$S3_BUCKET/$S3_KEY"
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
rm /mnt/tiles/lock
