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
import datetime
import click

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
                    output += buf.decode("utf-8")

                if output != "" and str.strip(output) != "":
                    print(f"{pre_log} {output}", end="", flush=True)

            return proc


# do we need this? we need to just tell if the dataset contains a geography it's not a bad check
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
            (geometry != '') OR (point != '')
        """
    )
    geography_datasets = [x[0] for x in cur]
    return geography_datasets


def create_geojson_from_wkt(entity_model_path):
    no_errors = False
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print(
        f"{current_time}: {LOG_INIT} started creating geojson for {entity_model_path}",
        flush=True,
    )
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
                print(
                    f"{LOG_INIT} ERROR in create_geojson_from_wkt - No data for entity_id: {entity_id})"
                )
                continue

            geo_json = geojson.Feature(geometry=geometry)
            del geo_json["properties"]

            cur.execute(
                """
                UPDATE  entity
                SET     geojson = ?
                WHERE   entity = ?
                """,
                (json.dumps(geo_json), entity_id),
            )

        conn.commit()
        no_errors = True

    except SQL_Error as exc:
        print(
            f"{LOG_INIT} ERROR in create_geojson_from_wkt for {entity_model_path}: {exc}"
        )
        return no_errors
    finally:
        conn.close()
        print(
            f"{LOG_INIT} finished processing create_geojson_from_wkt for {entity_model_path}",
            flush=True,
        )
        return no_errors


def get_dataset_features(entity_model_path, dataset=None):
    # removed organisation table properties may need to be added back iin if replaced by postgis
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


# def create_geojson_file(features, output_path, dataset):
#     geojson = '{"type":"FeatureCollection","features":[' + features + "]}"
#     with open(f"{output_path}/{dataset}.geojson", "w") as f:
#         f.write(geojson)
#     print(f"{LOG_INIT} [{dataset}] created geojson", flush=True)


def create_geojson_file(features, output_path, dataset):
    print("features: ", features)
    batch_size = 50000
    num_features = len(features)

    with open(f"{output_path}/{dataset}.geojson", "w") as f:
        f.write('{"type":"FeatureCollection","features":[')

        for start_index in range(0, num_features, batch_size):
            # end_index = min(start_index + batch_size, num_features)
            batch_features = features[start_index : start_index + batch_size]

            # if start_index > 0:
            #     f.write(',')  # Add comma between GeoJSON objects

            # geojson = {"type": "FeatureCollection", "features": batch_features}
            f.write(batch_features)
            # print(f"Processed features {start_index+1}-{end_index} of {num_features} for [{dataset}]", flush=True)

        f.write("]}")


def build_dataset_tiles(output_path, dataset):
    build_tiles_cmd = (
        f"tippecanoe --no-progress-indicator -z15 -Z4 -r1 --no-feature-limit "
        f"--no-tile-size-limit --layer={dataset} --output={output_path}/{dataset}.mbtiles "
        f"{output_path}/{dataset}.geojson "
    )
    proc = run(build_tiles_cmd, f"{LOG_INIT} [{dataset}]")
    if proc.returncode != 0:
        print(f"{LOG_INIT} [{dataset}] failed to create tiles", flush=True)
    else:
        current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
        print(f"{current_time}: {LOG_INIT} [{dataset}] created tiles", flush=True)


def build_tiles(entity_path, output_path, dataset):
    features = get_dataset_features(entity_path, dataset)
    print(f"{LOG_INIT} [{dataset}] started processing", flush=True)
    create_geojson_file(features, output_path, dataset)
    build_dataset_tiles(output_path, dataset)


@click.command()
@click.option(
    "--entity-path",
    type=click.Path(exists=True),
    default=Path("var/cache/entity.sqlite3"),
    help="Path to the entity database",
)
@click.option(
    "--output-dir",
    type=click.Path(exists=True),
    default=Path("var/cache/"),
    help="Path to the output directory",
)
def main(entity_path, output_dir):
    datasets = get_geography_datasets(entity_path)
    if datasets is None:
        print(f"{LOG_INIT}: No datasets found: {entity_path}", flush=True)
        exit(1)

    print(f"{LOG_INIT} found datasets: {datasets}", flush=True)

    result = create_geojson_from_wkt(entity_path)
    if not result:
        print(f"{LOG_INIT} ERROR processing create_geojson_from_wkt", flush=True)
        exit(1)

    for d in datasets:
        build_tiles(entity_path, output_dir, d)


if __name__ == "__main__":
    main()
