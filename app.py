import logging
from pathlib import Path
from datasette.app import Datasette

datasets = [d for d in Path(".").rglob("*.mbtiles")]

logger = logging.getLogger("gunicorn.error")
logger.info(f"Starting server with datasets: {datasets}")

app = Datasette(
    datasets,
    config_dir=Path("."),
    sqlite_extensions=["spatialite"],
).app()
