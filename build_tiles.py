import argparse
import sqlite3
import subprocess
import multiprocessing as mp
from pathlib import Path
from itertools import repeat


def run(command):
    proc = subprocess.run(command, capture_output=True, text=True)
    try:
        proc.check_returncode()  # raise exception on nonz-ero return code
    except subprocess.CalledProcessError as e:
        print(f"\n---- STDERR ----\n{proc.stderr}")
        print(f"\n---- STDOUT ----\n{proc.stdout}")
        raise e

    return proc


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
        "'type'",
        "entity.dataset",
        "'organisation'",
        "oe.name",
        "'entity'",
        "entity.entity",
        "'entry-date'",
        "entity.entry_date",
        "'start-date'",
        "entity.start_date",
        "'end-date'",
        "entity.end_date" ")",
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
        """.format(
        properties=",".join(json_properties)
    )

    cur = conn.cursor()
    if dataset:
        query += "WHERE entity.dataset == ?"
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


def build_dataset_tiles(output_path, dataset):
    build_tiles_cmd = [
        "tippecanoe",
        "-z15",
        "-Z4",
        "-r1",
        "--no-feature-limit",
        "--no-tile-size-limit",
        f"--layer={dataset}",
        f"--output={output_path}/{dataset}.mbtiles",
        f"{output_path}/{dataset}.geojson",
    ]
    run(build_tiles_cmd)


def build_tiles(entity_path, output_path, dataset):
    print(dataset)
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
    with mp.Pool(mp.cpu_count()) as pool:
        pool.starmap(
            build_tiles, zip(repeat(entity_path), repeat(output_path), datasets)
        )
