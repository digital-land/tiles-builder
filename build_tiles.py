import argparse
import json
import os

import geojson
import shapely.wkt
from select import select
import sqlite3
from sqlite3 import Error as SQL_Error
import subprocess
from pathlib import Path
from contextlib import contextmanager

LOG_INIT = f"{os.getenv('EVENT_ID')}:"


@contextmanager
def pipe():
    r, w = os.pipe()
    yield r, w
    os.close(r)
    os.close(w)


def run(command, pre_log):
    with pipe() as (r, w):
        with subprocess.Popen(command, shell=True, stdout=w, stderr=w) as proc:
            while proc.poll() is None:
                output = ""
                while len(select([r], [], [], 0)[0]) > 0:
                    buf = os.read(r, 1024)
                    output += buf.decode('utf-8')

                if output != '' and str.strip(output) != '':
                    print(f"{pre_log} {output}", end='', flush=True)

            return proc


def get_geography_datasets(entity_model_path):
    if not Path(entity_model_path).is_file():
        return None

    conn = sqlite3.connect(entity_model_path)
    cur = conn.cursor()
    cur.execute(
        """
        SELECT
            DISTINCT dataset
        FROM
            entity
        WHERE
            geojson == ''
        AND
            (geometry != '') OR (point != '')
        """
    )
    geography_datasets = [x[0] for x in cur]
    return geography_datasets


def create_geojson_from_wkt(entity_model_path):
    no_errors = False
    print(f"{LOG_INIT} started creating geojson for {entity_model_path}", flush=True)
    conn = sqlite3.connect(entity_model_path)

    try:
        cur = conn.cursor()
        cur.execute(
            """
            SELECT      entity,
                        point,
                        geometry
            FROM        entity
            WHERE       geometry != ''
            OR          point != ''
            ORDER BY    entity
            """
        )

        source_rows = [[row[0], row[1], row[2]] for row in cur]

        for row in source_rows:

            entity_id = row[0] or None
            point = row[1] or None
            shape = row[2] or None

            if shape:
                geometry = shapely.wkt.loads(shape)
            elif point:
                geometry = shapely.wkt.loads(point)
            else:
                print(f"{LOG_INIT} ERROR in create_geojson_from_wkt - No data for entity_id: {entity_id})")
                continue

            geo_json = geojson.Feature(geometry=geometry)
            del geo_json["properties"]

            cur.execute(
                """
                UPDATE  entity
                SET     geojson = ?
                WHERE   entity = ?
                """,
                (json.dumps(geo_json), entity_id)
            )

        conn.commit()
        no_errors = True

    except SQL_Error as exc:
        print(f"{LOG_INIT} ERROR in create_geojson_from_wkt for {entity_model_path}: {exc}")
        return no_errors
    finally:
        conn.close()
        print(f"{LOG_INIT} finished processing create_geojson_from_wkt for {entity_model_path}", flush=True)
        return no_errors


def get_dataset_features(entity_model_path, dataset=None):
    conn = sqlite3.connect(entity_model_path)
    json_properties = [
        "'tippecanoe'",
        "json_object('layer', entity.dataset)",
        "'entity'",
        "entity.entity",
        "'properties'",
        "json_patch(" "json_object(" "'name'",
        "entity.name",
        "'dataset'",
        "entity.dataset",
        "'organisation-entity'",
        "entity.organisation_entity",
        "'organisation-name'",
        "oe.name",
        "'entity'",
        "entity.entity",
        "'entry-date'",
        "entity.entry_date",
        "'start-date'",
        "entity.start_date",
        "'end-date'",
        "entity.end_date",
        "'prefix'",
        "entity.prefix",
        "'reference'",
        "entity.reference" ")",
        "IFNULL(entity.json, '{}')" ")",
    ]
    query = """
        SELECT
            json_patch(entity.geojson,
            json_object({properties}))
        FROM
            entity
        LEFT JOIN entity AS oe
        ON entity.organisation_entity = oe.entity
        WHERE NOT EXISTS (
            SELECT * FROM old_entity
                WHERE entity.entity = old_entity.old_entity
        )
        AND entity.geojson != ''
        """.format(
        properties=",".join(json_properties)
    )

    cur = conn.cursor()
    if dataset:
        query += "AND entity.dataset == ?"
        cur.execute(query, (dataset,))
    else:
        cur.execute(query)

    results = ",".join(x[0] for x in cur)
    results = results.rstrip(",")

    return results


def create_geojson_file(features, output_path, dataset):
    geojson = '{"type":"FeatureCollection","features":[' + features + "]}"
    with open(f"{output_path}/{dataset}.geojson", "w") as f:
        f.write(geojson)
    print(f"{LOG_INIT} [{dataset}] created geojson", flush=True)


def build_dataset_tiles(output_path, dataset):
    build_tiles_cmd = f"tippecanoe --no-progress-indicator -z15 -Z4 -r1 --no-feature-limit " \
                      f"--no-tile-size-limit --layer={dataset} --output={output_path}/{dataset}.mbtiles " \
                      f"{output_path}/{dataset}.geojson "
    proc = run(build_tiles_cmd, f"{LOG_INIT} [{dataset}]")
    if proc.returncode != 0:
        print(f"{LOG_INIT} [{dataset}] failed to create tiles", flush=True)
    else:
        print(f"{LOG_INIT} [{dataset}] created tiles", flush=True)


def build_tiles(entity_path, output_path, dataset):
    features = get_dataset_features(entity_path, dataset)

    if dataset is None:
        dataset = "dataset_tiles"

        # New addition
        # When run for the first time, dataset_tiles.geojson does not exist
        # in the output directory, and is generated as part of the dataset run.
        # This change ensures that successive dataset runs append to dataset_tiles.geojson.
        # The end result is that, after all datasets have been run, dataset_tiles.geojson
        # and dataset_tiles.mbtiles contain information from all the datasets.
        # This file is required downstream as at: Spring '23
        #
        # change postponed
        # parent_output_path = str(Path(output_path).parent.absolute())
        # previous_dataset_tiles_geojson = f"{parent_output_path}/dataset_tiles.geojson"
        # if Path(previous_dataset_tiles_geojson).exists():
        #     shutil.copy(previous_dataset_tiles_geojson, output_path)

    print(f"{LOG_INIT} [{dataset}] started processing", flush=True)

    create_geojson_file(features, output_path, dataset)
    build_dataset_tiles(output_path, dataset)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Script to build mbtiles databases")
    parser.add_argument(
        "--entity-path",
        type=Path,
        nargs=1,
        required=False,
        default=Path("var/cache/entity.sqlite3"),
        help="Path to the entity database",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        nargs=1,
        required=False,
        default=Path("var/cache/"),
        help="The numbers available to use (six must be provided)",
    )
    cmd_args = parser.parse_args()
    entity_path = cmd_args.entity_path[0]
    output_path = cmd_args.output_dir[0]
    datasets = get_geography_datasets(entity_path)
    if datasets is None:
        print(f"{LOG_INIT}: No datasets found: {entity_path}", flush=True)
        exit(1)

    print(f"{LOG_INIT} found datasets: {datasets}", flush=True)
    datasets.append(None)

    result = create_geojson_from_wkt(entity_path)
    if not result:
        print(f"{LOG_INIT} ERROR processing create_geojson_from_wkt", flush=True)
        exit(1)

    for d in datasets:
        build_tiles(entity_path, output_path, d)
