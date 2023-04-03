import os
import shutil

from pathlib import Path
import pytest

from task.build_tiles import get_geography_datasets, create_geojson_from_wkt, build_tiles


@pytest.fixture
def env_vars(request):

    root_dir = request.config.rootdir
    tests_dir = Path(root_dir).resolve().parent.parent

    return {
        "data_landing": f"{tests_dir}/data/landing",
        "data_clean": f"{tests_dir}/data/clean",
        "data_curated": f"{tests_dir}/data/curated",
        "data_remote": f"{tests_dir}/data/remote",
        "EVENT_ID": "[test_tile-builder]",
        "S3_KEY": "entity-builder/dataset/national-park.sqlite3",
        "S3_BUCKET": "production-collection-data",
        "DATABASE": "national-park.sqlite3",  # world-heritage-site.sqlite3
        "DATABASE_NAME": "national-park",     # world-heritage-site
    }


def test_clean_curated_dir(env_vars):
    data_curated_db = f"{env_vars['data_curated']}/{env_vars['DATABASE']}"
    data_curated_tiles = f"{env_vars['data_curated']}/tiles"

    if os.path.isfile(data_curated_db):
        os.remove(data_curated_db)

    if os.path.isdir(data_curated_tiles):
        shutil.rmtree(data_curated_tiles)


def test_copy_db_from_remote(env_vars):
    data_remote = f"{env_vars['data_remote']}/{env_vars['DATABASE']}"
    data_landing = f"{env_vars['data_landing']}"

    shutil.copy(data_remote, data_landing)


def test_build_tiles(env_vars):
    entity_path = f"{env_vars['data_landing']}/{env_vars['DATABASE']}"
    output_path = f"{env_vars['data_landing']}/tiles/temporary"

    datasets = get_geography_datasets(entity_path)
    assert datasets is not None

    datasets.append(None)

    result = create_geojson_from_wkt(entity_path)
    assert result is True

    if not os.path.exists(output_path):
        os.makedirs(output_path)

    for ds in datasets:
        build_tiles(entity_path, output_path, ds)


def test_move_db_and_tiles_from_landing(env_vars):
    data_landing = f"{env_vars['data_landing']}/{env_vars['DATABASE']}"
    data_curated = f"{env_vars['data_curated']}"

    shutil.move(data_landing, data_curated)

    data_landing_tmp = f"{env_vars['data_landing']}/tiles/temporary"
    data_landing_tiles = f"{env_vars['data_landing']}/tiles"
    data_curated_tiles = f"{env_vars['data_curated']}/tiles"

    shutil.move(data_landing_tmp, data_curated_tiles)
    shutil.rmtree(data_landing_tiles)

