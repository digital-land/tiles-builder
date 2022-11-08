#!/usr/bin/env bash

DATASETTE_PID=0
ls

start_datasette() {
  DATASETTE_SERVE_ARGS="-h 0.0.0.0 -p $PORT --setting sql_time_limit_ms 8000 --nolock "

  for TILES_FILE in /mnt/tiles/*.mbtiles; do
    DATASETTE_SERVE_ARGS+="--immutable=$TILES_FILE "
  done

  DATASETTE_SERVE_ARGS+=" --plugins-dir ./plugins"

  echo "Starting datasette service with args $DATASETTE_SERVE_ARGS"
  if [[ "$DATASETTE_PID" -ne "0" ]]; then kill $DATASETTE_PID; fi
  datasette serve ${DATASETTE_SERVE_ARGS} & DATASETTE_PID=$! || exit 1
  echo "Datasette started with PID $DATASETTE_PID"
}

start_datasette
CURRENT_CHECKSUM=$(sha256sum  /mnt/tiles/updated)

while [[ 1=1 ]]; do
  if echo "$CURRENT_CHECKSUM" | sha256sum --check --status; then
    true
  else
    echo "/mnt/tiles/updated has changed, restarting datasette"
    CURRENT_CHECKSUM=$(sha256sum  /mnt/tiles/updated)
    start_datasette
  fi
  sleep 10
done
