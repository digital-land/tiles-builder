import os
import shutil
import logging
from pathlib import Path
import urllib.request
import pytest
import importlib
import click
from click.testing import CliRunner

from task.build_tiles import get_geography_datasets, create_geojson_from_wkt, build_tiles,main

@pytest.fixture
def central_activities_sqlite_path(tmp_path):
    dataset_path = os.path.join(tmp_path, "central-activities-zone.sqlite3")
    urllib.request.urlretrieve(
        "https://files.planning.data.gov.uk/central-activities-zone-collection/dataset/central-activities-zone.sqlite3",
        dataset_path
    )

    return dataset_path
# @pytest.fixture
# def env_vars(request):

#     root_dir = request.config.rootdir
#     tests_dir = Path(root_dir).resolve().parent.parent

#     return {
#         "data_landing": f"{tests_dir}/data/landing",
#         "data_clean": f"{tests_dir}/data/clean",
#         "data_curated": f"{tests_dir}/data/curated",
#         "data_remote": f"{tests_dir}/data/remote",
#         "EVENT_ID": "[test_tile-builder]",
#         "S3_KEY": "entity-builder/dataset/national-park.sqlite3",
#         "S3_BUCKET": "production-collection-data",
#         "DATABASE": "national-park.sqlite3",  # world-heritage-site.sqlite3
#         "DATABASE_NAME": "national-park",     # world-heritage-site
#     }


# def test_clean_curated_dir(env_vars):
#     data_curated_db = f"{env_vars['data_curated']}/{env_vars['DATABASE']}"
#     data_curated_tiles = f"{env_vars['data_curated']}/tiles"

#     if os.path.isfile(data_curated_db):
#         os.remove(data_curated_db)

#     if os.path.isdir(data_curated_tiles):
#         shutil.rmtree(data_curated_tiles)


# def test_copy_db_from_remote(env_vars):
#     data_remote = f"{env_vars['data_remote']}/{env_vars['DATABASE']}"
#     data_landing = f"{env_vars['data_landing']}"

#     shutil.copy(data_remote, data_landing)


def test_main(tmp_path,central_activities_sqlite_path):
    tiles_path = os.path.join(tmp_path,'tiles')
    logging.warning(tiles_path)
    os.mkdir(tiles_path)
    runner = CliRunner()
    # result = runner.invoke(main, f'--entity-path {central_activities_sqlite_path} --output-dir {tmp_path}/tiles'.split())
    result = runner.invoke(main,['--entity-path',f'{central_activities_sqlite_path}','--output-dir',f'{tiles_path}'])
    logging.warning(result)
    assert result.exit_code == 0
    assert os.path.exists(f'{tmp_path}/tiles/central-activities-zone.mbtiles')


# def test_move_db_and_tiles_from_landing(env_vars):
#     data_landing = f"{env_vars['data_landing']}/{env_vars['DATABASE']}"
#     data_curated = f"{env_vars['data_curated']}"

#     shutil.move(data_landing, data_curated)

#     data_landing_tmp = f"{env_vars['data_landing']}/tiles/temporary"
#     data_landing_tiles = f"{env_vars['data_landing']}/tiles"
#     data_curated_tiles = f"{env_vars['data_curated']}/tiles"

#     shutil.move(data_landing_tmp, data_curated_tiles)
#     shutil.rmtree(data_landing_tiles)

