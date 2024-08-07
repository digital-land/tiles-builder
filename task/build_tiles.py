import json
import os
import geojson
import shapely.wkt
from select import select
import sqlite3
import subprocess
from pathlib import Path
from contextlib import contextmanager
import datetime
import hashlib
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
        update_cursor = conn.cursor()
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

        batch_size = 10000

        while True:
            rows = cur.fetchmany(batch_size)
            if not rows:
                no_errors = True
                break
            for row in rows:
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
                update_cursor.execute(
                    """
                    UPDATE  entity
                    SET     geojson = ?
                    WHERE   entity = ?
                    """,
                    (json.dumps(geo_json), entity_id),
                )

            no_errors = True
        conn.commit()

    except sqlite3.Error as exc:
        print(
            f"{LOG_INIT} ERROR in create_geojson_from_wkt for {entity_model_path}: {exc}"
        )
    finally:
        cur.close()
        update_cursor.close()
        conn.close()
        print(
            f"{LOG_INIT} finished processing create_geojson_from_wkt for {entity_model_path}",
            flush=True,
        )
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


def create_geojson_file(features, output_path, dataset):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print(f"{current_time}: started creating geojson file")
    geojson = '{"type":"FeatureCollection","features":[' + features + "]}"
    with open(f"{output_path}/{dataset}.geojson", "w") as f:
        f.write(geojson)
    print(f"{LOG_INIT} [{dataset}] created geojson", flush=True)


def build_dataset_tiles(output_path, dataset):
    current_time = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")
    print(f"{current_time}: Started building tiles - build_dataset_tiles")
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


def get_current_sqlite_hash(sqlite_path):
    print(f"{LOG_INIT} Attempting to get_current_sqlite_hash for sqlite_path={sqlite_path}", flush=True)
    with open(sqlite_path, "rb") as f:
        sqlite_data = f.read()
    return hashlib.md5(sqlite_data).hexdigest()


def get_stored_hash(hash_path):
    if hash_path.exists():
        with open(hash_path) as file:
            return json.load(file).get("hash")
    return None


def update_current_sqlite_hash(hash_path, new_hash):
    with open(hash_path, "w") as file:
        hash_dict = {"hash": new_hash}
        file.write(json.dumps(hash_dict))


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
@click.option(
    "--hash-dir",
    type=click.Path(),
    default=Path("var/cache/hashes/"),
    help="Path to the directory for storing hashes",
)
@click.option(
    "--hash-check-enabled",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
            "Flag whether a hash check should be performed. Disabling the check can be useful in the scenario "
            "where a rebuild of tile data is required even when SQLite data has not changed.")
)
@click.option(
    "--hash-generation-enabled",
    is_flag=True,
    show_default=True,
    default=False,
    help=(
            "Flag whether a hash should be generated. Disabling the check can be useful in the scenario "
            "that hash generation is causing any problem.")
)
def main(entity_path, output_dir, hash_dir, hash_check_enabled=False, hash_generation_enabled=False):
    print(f"{LOG_INIT} hash_check_enabled: {hash_check_enabled}", flush=True)
    print(f"{LOG_INIT} hash_generation_enabled: {hash_generation_enabled}", flush=True)

    Path(hash_dir).mkdir(parents=True, exist_ok=True)
    datasets = get_geography_datasets(entity_path)
    if datasets is None:
        print(f"{LOG_INIT}: No datasets found: {entity_path}", flush=True)
        exit(1)

    print(f"{LOG_INIT} found datasets: {datasets}", flush=True)

    hash_path = Path(hash_dir) / f"{Path(entity_path).stem}.json"
    print(f"hash_path: {hash_path}", flush=True)
    stored_hash = get_stored_hash(hash_path)
    print(f"stored_hash: {stored_hash}", flush=True)

    current_hash = get_current_sqlite_hash(entity_path) if hash_generation_enabled else None
    print(f"current_hash: {current_hash}", flush=True)

    if hash_check_enabled and current_hash == stored_hash:
        print(f"{LOG_INIT} No changes detected. Skipping tile update.", flush=True)
        exit(1)

    print("Calling create_geojson_from_wkt", flush=True)
    result = create_geojson_from_wkt(entity_path)
    print("Called create_geojson_from_wkt", flush=True)
    if not result:
        print(f"{LOG_INIT} ERROR processing create_geojson_from_wkt", flush=True)
        exit(1)
    for d in datasets:
        build_tiles(entity_path, output_dir, d)
    if hash_generation_enabled:
        update_current_sqlite_hash(hash_path, current_hash)
    print(f"{LOG_INIT} Tiles built successfully.", flush=True)


if __name__ == "__main__":
    main()
