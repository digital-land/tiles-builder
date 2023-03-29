import os.path
import pathlib

import pandas as pd
import pytest
import sqlite3

from task.build_tiles import get_geography_datasets, create_geojson_from_wkt, get_dataset_features
from tests.helpers.expectations import QueryRunner, expect_filtered_entities_to_be_as_predicted


@pytest.fixture
def env_vars():
    yield {
        "data_landing": "../../data/landing",
        "data_clean": "../../data/clean",
        "data_curated": "../../data/curated",
        "data_remote": "../../data/remote",
        "EVENT_ID": "[test_tile-builder]",
        "S3_KEY": "entity-builder/dataset/national-park.sqlite3",
        "S3_BUCKET": "production-collection-data",
        "DATABASE": "national-park.sqlite3",  # world-heritage-site.sqlite3
        "DATABASE_NAME": "national-park",     # world-heritage-site
    }


@pytest.fixture
def test_dataset_db_path(env_vars):
    dataset_path = f"{env_vars['data_landing']}/test.sqlite3"

    create_table_sql = """
        create table entity
        (
            dataset             TEXT,
            end_date            TEXT,
            entity              INTEGER primary key,
            entry_date          TEXT,
            geojson             JSON,
            geometry            TEXT,
            json                JSON,
            name                TEXT,
            organisation_entity TEXT,
            point               TEXT,
            prefix              TEXT,
            reference           TEXT,
            start_date          TEXT,
            typology            TEXT
        )    
    """

    with sqlite3.connect(dataset_path) as conn:
        conn.execute(create_table_sql)
    conn.close()

    yield dataset_path

    # pathlib.Path(dataset_path).unlink()
    if os.path.isfile(dataset_path):
        os.remove(dataset_path)


def test_get_geography_datasets_for_national_park(env_vars):
    entity_path = f"{env_vars['data_landing']}/{env_vars['DATABASE']}"
    output_path = f"{env_vars['data_landing']}/tiles/temporary"

    result = get_geography_datasets(entity_path)
    assert env_vars["DATABASE_NAME"] == "national-park"
    assert result == ["national-park"]


def test_get_geography_datasets_for_world_heritage_site(env_vars):
    env_vars["DATABASE"] = "world-heritage-site.sqlite3"
    env_vars["DATABASE_NAME"] = "world-heritage-site"

    entity_path = f"{env_vars['data_landing']}/{env_vars['DATABASE']}"
    output_path = f"{env_vars['data_landing']}/tiles/temporary"

    result = get_geography_datasets(entity_path)
    assert env_vars["DATABASE_NAME"] == "world-heritage-site"
    assert result == ["world-heritage-site"]


def test_get_geography_datasets_returns_none_when_DATABASE_NAME_empty(env_vars):
    env_vars["DATABASE"] = ""
    env_vars["DATABASE_NAME"] = ""

    entity_path = f"{env_vars['data_landing']}/{env_vars['DATABASE']}"
    output_path = f"{env_vars['data_landing']}/tiles/temporary"

    result = get_geography_datasets(entity_path)
    assert result is None

    # with pytest.raises(IOError):
    #     result = get_geography_datasets(entity_path)


def test_create_geojson_from_wkt_returns_true_with_good_data(env_vars):
    env_vars["DATABASE"] = "national-park.sqlite3"
    env_vars["DATABASE_NAME"] = "national-park"

    entity_path = f"{env_vars['data_landing']}/{env_vars['DATABASE']}"
    output_path = f"{env_vars['data_landing']}/tiles/temporary"

    result = create_geojson_from_wkt(entity_path)
    assert result is True

    # with pytest.raises(IOError):
    #     result = get_geography_datasets(entity_path)


def test_get_dataset_features_returns_value_for_good_data(env_vars):
    entity_path = f"{env_vars['data_landing']}/{env_vars['DATABASE']}"
    output_path = f"{env_vars['data_landing']}/tiles/temporary"

    datasets = get_geography_datasets(entity_path)
    result = get_dataset_features(entity_path, datasets[0])
    assert result != ""


def test_create_geojson_from_wkt_with_only_point_data(env_vars, test_dataset_db_path):

    # arrange
    test_data = pd.DataFrame.from_dict(
        {
            "dataset": ["national-park", "national-park"],
            "entity": [520001, 520002],
            "geojson": ["", ""],
            "geometry": ["", ""],
            "point": ["POINT(-3.905559 50.582137)", "POINT(-3.652891 51.142985)"],
            "reference": ["1", "2"]
        }
    )

    with sqlite3.connect(test_dataset_db_path) as conn:
        test_data.to_sql("entity", conn, if_exists="append", index=False)
    conn.close()

    # act
    sut_result = create_geojson_from_wkt(test_dataset_db_path)

    # assert
    query_runner = QueryRunner(test_dataset_db_path)

    expected_value = '{"type": "Feature", "geometry": {"type": "Point", "coordinates": [-3.905559, 50.582137]}}'
    expected_result = [{'geojson': expected_value}]
    columns = ["geojson"]
    filters = {"reference": "1"}

    result, msg, details = expect_filtered_entities_to_be_as_predicted(
        query_runner=query_runner,
        expected_result=expected_result,
        columns=columns,
        filters=filters
    )

    assert sut_result is True
    assert result, f"Expectation Details: {details}"



