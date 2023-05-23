import json
import pandas as pd
import pytest
import sqlite3

from task.build_tiles import (
    get_geography_datasets,
    create_geojson_from_wkt,
    get_dataset_features,
)


@pytest.fixture
def entity_sqlite_path(tmp_path):
    dataset_path = f"{tmp_path}/test.sqlite3"

    create_entity_table_sql = """
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
        conn.execute(create_entity_table_sql)
    conn.close()

    create_old_entity_table_sql = """
        CREATE TABLE old_entity (end_date TEXT,
            entity INTEGER,
            entry_date TEXT,
            notes TEXT,
            old_entity TEXT PRIMARY KEY,
            start_date TEXT,
            status TEXT, FOREIGN KEY (entity) REFERENCES entity (entity))
    """

    with sqlite3.connect(dataset_path) as conn:
        conn.execute(create_old_entity_table_sql)
    conn.close()

    return dataset_path


def test_get_geography_datasets_for_single_dataset(entity_sqlite_path):
    test_data = pd.DataFrame.from_dict(
        {
            "dataset": ["central-activities-zone", "central-activities-zone"],
            "entity": [520001, 520002],
            "geojson": ["", ""],
            "geometry": ["", ""],
            "point": ["POINT(-3.905559 50.582137)", "POINT(-3.652891 51.142985)"],
            "reference": ["1", "2"],
        }
    )

    with sqlite3.connect(entity_sqlite_path) as conn:
        test_data.to_sql("entity", conn, if_exists="append", index=False)
    conn.close()

    result = get_geography_datasets(entity_sqlite_path)
    assert result == ["central-activities-zone"]


def test_get_geography_datasets_for_multiple_datasets(entity_sqlite_path):
    test_data = pd.DataFrame.from_dict(
        {
            "dataset": ["national-park", "central-activities-zone"],
            "entity": [520001, 520002],
            "geojson": ["", ""],
            "geometry": ["", ""],
            "point": ["POINT(-3.905559 50.582137)", "POINT(-3.652891 51.142985)"],
            "reference": ["1", "2"],
        }
    )

    with sqlite3.connect(entity_sqlite_path) as conn:
        test_data.to_sql("entity", conn, if_exists="append", index=False)
    conn.close()

    result = get_geography_datasets(entity_sqlite_path)
    assert result == ["national-park", "central-activities-zone"]


def test_get_geography_datasets_does_not_return_non_geography_datasets(
    entity_sqlite_path,
):
    test_data = pd.DataFrame.from_dict(
        {
            "dataset": ["article-4-direction"],
            "entity": [520001],
            "geojson": [""],
            "geometry": [""],
            "point": [""],
            "reference": ["1"],
        }
    )

    with sqlite3.connect(entity_sqlite_path) as conn:
        test_data.to_sql("entity", conn, if_exists="append", index=False)
    conn.close()

    result = get_geography_datasets(entity_sqlite_path)
    assert result == []


def test_get_geography_datasets_returns_none_for_empty_db(entity_sqlite_path):
    result = get_geography_datasets(entity_sqlite_path)
    assert result == []


def test_create_geojson_from_wkt_with_geometry_data(entity_sqlite_path):
    test_data = pd.DataFrame.from_dict(
        {
            "dataset": ["central-activities-zone"],
            "entity": [520001],
            "geojson": [""],
            "geometry": [
                "MULTIPOLYGON (((1.085705 51.280868,1.085752 51.280805,1.086082 51.280894,1.086030 51.280952,1.085705 51.280868)))"  # noqa: E501
            ],
            "point": ["POINT(1.085891 51.280879)"],
            "reference": ["1"],
        }
    )

    with sqlite3.connect(entity_sqlite_path) as conn:
        test_data.to_sql("entity", conn, if_exists="append", index=False)
    conn.close()

    result = create_geojson_from_wkt(entity_sqlite_path)
    assert result is True
    # check multiploygon is the type of the geojson
    sql = "SELECT geojson FROM entity where entity = 520001;"
    with sqlite3.connect(entity_sqlite_path) as con:
        cursor = con.execute(sql)
        cols = [column[0] for column in cursor.description]
        results = pd.DataFrame.from_records(data=cursor.fetchall(), columns=cols)

    geojson_output = json.loads(results["geojson"][0])
    assert geojson_output["geometry"]["type"] == "MultiPolygon"


def test_create_geojson_from_wkt_with_only_point_data(entity_sqlite_path):
    # arrange
    test_data = pd.DataFrame.from_dict(
        {
            "dataset": ["national-park", "national-park"],
            "entity": [520001, 520002],
            "geojson": ["", ""],
            "geometry": ["", ""],
            "point": ["POINT(-3.905559 50.582137)", "POINT(-3.652891 51.142985)"],
            "reference": ["1", "2"],
        }
    )

    with sqlite3.connect(entity_sqlite_path) as conn:
        test_data.to_sql("entity", conn, if_exists="append", index=False)
    conn.close()

    # act
    result = create_geojson_from_wkt(entity_sqlite_path)
    assert result

    # assert
    sql = "SELECT geojson FROM entity where entity = 520001;"
    with sqlite3.connect(entity_sqlite_path) as con:
        cursor = con.execute(sql)
        cols = [column[0] for column in cursor.description]
        results = pd.DataFrame.from_records(data=cursor.fetchall(), columns=cols)

    geojson_output = json.loads(results["geojson"][0])
    assert geojson_output["geometry"]["type"] == "Point"


def test_get_dataset_features_returns_value_for_good_data(entity_sqlite_path):
    test_data = pd.DataFrame.from_dict(
        {
            "dataset": ["central-activities-zone"],
            "entity": [520001],
            "name": ["test1"],
            "organisation_entity": ["212"],
            "geojson": [
                '{"geometry": {"coordinates": [-3.905559, 50.582137], "type": "Point"}, "type": "Feature"}'
            ],
            "geometry": [""],
            "point": ["POINT(-3.905559 50.582137)"],
            "reference": ["1"],
        }
    )

    with sqlite3.connect(entity_sqlite_path) as conn:
        test_data.to_sql("entity", conn, if_exists="append", index=False)
    conn.close()

    result = get_dataset_features(entity_sqlite_path, "central-activities-zone")
    assert result != ""
