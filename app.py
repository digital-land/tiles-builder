import logging
from pathlib import Path

from datasette.app import Datasette
from environs import Env

env = Env()
datasets = env.list("DIGITAL_LAND_DATASETS")

logger = logging.getLogger("gunicorn.error")
logger.info(f"Starting server with datasets: {datasets}")

app = Datasette(
    datasets,
    config_dir=Path("."),
    sqlite_extensions=["spatialite"],
).app()
