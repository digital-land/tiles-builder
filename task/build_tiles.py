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

            if proc.returncode != 0:
                print(f"{pre_log} ERROR: Command failed with return code {proc.returncode}")

            return proc


def get_geography_datasets(entity_model_path):
    if not Path(entity_model_path).is_file():
        print(f"{LOG_INIT} ERROR: Path does not exist: {entity_model_path}")
        return None

    try:
        conn = sqlite3.connect(entity_model_path)
        cur = conn.cursor()
        cur.execute(
            """
            SELECT DISTINCT dataset
            FROM entity
            WHERE (geometry != '') OR (point != '')
            """
        )
        geography_datasets = [x[0] for x in cur]
        conn.close()
        return geography_datasets
    except SQL_Error as e:
        print(f"{LOG_INIT} ERROR: Failed to retrieve datasets - {e}")
        return None


def process_entities(conn):
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT entity, point, geometry
            FROM entity
            WHERE geometry != '' OR point != ''
            ORDER BY entity
            """
        )

        batch = []
        batch_size = 500

        for entity_id, point, geometry in cursor:
            try:
                if geometry:
                    geo_obj = shapely.wkt.loads(geometry)
                elif point:
                    geo_obj = shapely.wkt.loads(point)
                else:
                    continue

                geo_json = geojson.Feature(geometry=geo_obj, properties={})
                batch.append((json.dumps(geo_json), entity_id))

                if len(batch) >= batch_size:
                    update_geojson_batch(conn, batch)
                    batch = []

            except Exception as e:
                print(f"{LOG_INIT} ERROR processing entity ID {entity_id}: {e}")

        if batch:
            update_geojson_batch(conn, batch)

        cursor.close()
    except SQL_Error as e:
        print(f"{LOG_INIT} ERROR during processing entities: {e}")


def update_geojson_batch(conn, updates):
    try:
        cursor = conn.cursor()
        cursor.executemany(
            """
            UPDATE entity
            SET geojson = ?
            WHERE entity = ?
            """,
            updates
        )
        conn.commit()
    except SQL_Error as e:
        print(f"{LOG_INIT} ERROR updating batch: {e}")


def get_dataset_features(entity_model_path, dataset=None):
    try:
        conn = sqlite3.connect(entity_model_path)
        cur = conn.cursor()
        query = """
            SELECT json_object(
                'type', 'FeatureCollection',
                'features', json_group_array(
                    json_object(
                        'type', 'Feature',
                        'geometry', json(json_extract(entity.geojson, '$.geometry')),
                        'properties', json_object(
                            'name', entity.name,
                            'dataset', entity.dataset,
                            'organisation-entity', entity.organisation_entity,
                            'entity', entity.entity,
                            'entry-date', entity.entry_date,
                            'start-date', entity.start_date,
                            'end-date', entity.end_date,
                            'prefix', entity.prefix,
                            'reference', entity.reference
                        )
                    )
                )
            )
            FROM entity
            WHERE entity.dataset = ? AND entity.geojson != ''
        """
        cur.execute(query, (dataset,))
        result = cur.fetchone()[0]
        conn.close()
        return result
    except SQL_Error as e:
        print(f"{LOG_INIT} ERROR fetching dataset features: {e}")
        return None


def create_geojson_file(features, output_path, dataset):
    if features:
        with open(f"{output_path}/{dataset}.geojson", "w") as f:
            f.write(features)
        print(f"{LOG_INIT} [{dataset}] created geojson", flush=True)
    else:
        print(f"{LOG_INIT} ERROR: No features to write for dataset {dataset}")

def build_dataset_tiles(output_path, dataset):
    build_tiles_cmd = (
        f"tippecanoe --no-progress-indicator -z15 -Z4 -r1 --no-feature-limit "
        f"--no-tile-size-limit --layer={dataset} --output={output_path}/{dataset}.mbtiles "
        f"{output_path}/{dataset}.geojson"
    )
    proc = run(build_tiles_cmd, f"{LOG_INIT} [{dataset}]")
    if proc.returncode != 0:
        print(f"{LOG_INIT} [{dataset}] failed to create tiles", flush=True)
    else:
        print(f"{LOG_INIT} [{dataset}] created tiles", flush=True)


def build_tiles(entity_path, output_path, dataset):
    conn = sqlite3.connect(entity_path)
    features = get_dataset_features(entity_path, dataset)
    if features:
        print(f"{LOG_INIT} [{dataset}] started processing", flush=True)
        create_geojson_file(features, output_path, dataset)
        build_dataset_tiles(output_path, dataset)
    else:
        print(f"{LOG_INIT} ERROR: No features found for dataset {dataset}")
    conn.close()


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

    conn = sqlite3.connect(entity_path)
    process_entities(conn)
    conn.close()

    for d in datasets:
        build_tiles(entity_path, output_dir, d)


if __name__ == "__main__":
    main()
