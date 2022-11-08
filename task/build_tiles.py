import argparse
import os
from select import select
import sqlite3
import subprocess
import multiprocessing as mp
from pathlib import Path
from itertools import repeat
from contextlib import contextmanager

LOG_INIT = f"{os.getenv('EVENT_ID')}:"


@contextmanager
def pipe():
    r, w = os.pipe()
    yield r, w
    os.close(r)
    os.close(w)


def run(command):
    with pipe() as (r, w):
        with subprocess.Popen(command, shell=True, stdout=w, stderr=w) as p:
            while p.poll() is None:
                # get read buffer from the output when ready without blocking
                while len(select([r], [], [], 0)[0]) > 0:
                    # read 1024 bytes from the buffer
                    buf = os.read(r, 1024)
                    print(f"{LOG_INIT} {buf.decode('utf-8')}", end='')


def get_geography_datasets(entity_model_path):
    conn = sqlite3.connect(entity_model_path)
    cur = conn.cursor()
    cur.execute(
        """
    SELECT
        DISTINCT dataset
    FROM
        entity
    WHERE geojson != ""
    """
    )
    geography_datasets = [x[0] for x in cur]
    conn.close()
    return geography_datasets


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
    print(f"{LOG_INIT} Creating geojson for {dataset}")

    with open(f"{output_path}/{dataset}.geojson", "w") as f:
        f.write(geojson)


def build_dataset_tiles(output_path, dataset):
    print(f"{LOG_INIT} Building dataset files for {dataset}")
    build_tiles_cmd = f"tippecanoe --no-progress-indicator --force -z15 -Z4 -r1 --no-feature-limit " \
                      f"--no-tile-size-limit --layer={dataset} --output={output_path}/{dataset}.mbti" \
                      f"les {output_path}/{dataset}.geojson "
    run(build_tiles_cmd)


def build_tiles(entity_path, output_path, dataset):
    features = get_dataset_features(entity_path, dataset)

    if dataset is None:
        dataset = "dataset_tiles"

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
    datasets.append(None)

    for d in datasets:
        print(f"{LOG_INIT} {d}")
        build_tiles(entity_path, output_path, d)
