from __future__ import annotations

import os

import uvicorn

from .api import create_app
from .config import Settings
from .logging_setup import configure_logging
from .monitor import OilSpillMonitor


def main() -> None:
    settings = Settings.from_env(os.getenv("ENV_FILE", ".env"))
    settings.ensure_directories()
    configure_logging(
        settings.log_level, settings.log_directory, settings.log_retention_days
    )
    monitor = OilSpillMonitor(settings)
    app = create_app(settings, monitor)
    uvicorn.run(
        app,
        host=settings.api_host,
        port=settings.api_port,
        workers=1,
        access_log=False,
    )


if __name__ == "__main__":
    main()
