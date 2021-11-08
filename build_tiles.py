import sqlite3
import subprocess
import multiprocessing as mp
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
    cur.execute("""
    SELECT
        DISTINCT dataset
    FROM
        entity
    JOIN geometry
    ON entity.entity = geometry.entity
    WHERE geometry.geojson != ""
    """)
    geography_datasets = [x[0] for x in cur]
    conn.close()
    return geography_datasets

def create_dataset_geojson(entity_model_path, dataset):
    conn = sqlite3.connect(entity_model_path)
    json_properties = [
        "'tippecanoe'", "json_object('layer', entity.dataset)",
        "'entity'", "entity.entity", 
        "'properties'", "json_patch("
            "json_object("
                "'name'", "entity.name",
                "'type'", "entity.dataset",
                "'organisation'", "oe.name", 
                "'entity'", "entity.entity",
                "'entry-date'", "entity.entry_date",
                "'start-date'", "entity.start_date",
                "'end-date'", "entity.end_date"
            ")",
            "IFNULL(entity.json, '{}')"
        ")"
        
    ]
    query = """
        SELECT
            json_patch(geometry.geojson, 
            json_object({properties}))
        FROM
            entity
        JOIN geometry
        ON entity.entity = geometry.entity
        LEFT JOIN entity AS oe 
        ON entity.organisation_entity = oe.entity
        WHERE entity.dataset == ? 
        """.format(properties=",".join(json_properties))

    print(query)
    cur = conn.cursor()
    cur.execute(query, 
    (dataset,))

    results = ",".join(x[0] for x in cur)
    results = results.rstrip(',')
    

    geojson = '{"type":"FeatureCollection","features":[' + results + ']}'

    with open(f"{dataset}.geojson", "w") as f:
         f.write(geojson)

def build_dataset_tiles(dataset):
    build_tiles_cmd = [
        "tippecanoe",
        "-z15",
        "-Z4",
        "-r1",
        "--no-feature-limit",
        "--no-tile-size-limit",
        f"--layer={dataset}",
        f"--output={dataset}.mbtiles",
        f"{dataset}.geojson",
    ]
    run(build_tiles_cmd)

def build_tiles(entity_model_path, dataset):
    print(dataset)
    create_dataset_geojson(entity_model_path, dataset)
    build_dataset_tiles(dataset)

    
if __name__ == "__main__":
    datasets = get_geography_datasets("entity.sqlite3")
    with mp.Pool(mp.cpu_count()) as pool:
        pool.starmap(build_tiles, zip(repeat("entity.sqlite3"), datasets))

