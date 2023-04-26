import os
import logging
import urllib.request
import pytest
from click.testing import CliRunner

from task.build_tiles import (
    main,
)


@pytest.fixture
def central_activities_sqlite_path(tmp_path):
    dataset_path = os.path.join(tmp_path, "central-activities-zone.sqlite3")
    urllib.request.urlretrieve(
        "https://files.planning.data.gov.uk/central-activities-zone-collection/dataset/central-activities-zone.sqlite3",
        dataset_path,
    )

    return dataset_path


def test_main(tmp_path, central_activities_sqlite_path):
    tiles_path = os.path.join(tmp_path, "tiles")
    os.mkdir(tiles_path)
    runner = CliRunner()
    result = runner.invoke(
        main,
        [
            "--entity-path",
            f"{central_activities_sqlite_path}",
            "--output-dir",
            f"{tiles_path}",
        ],
    )
    logging.warning(os.listdir(tiles_path))
    assert result.exit_code == 0
    assert os.path.exists(f"{tiles_path}/central-activities-zone.mbtiles")
