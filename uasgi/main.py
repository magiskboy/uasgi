from __future__ import annotations

import asyncio
from typing import Optional

import uvloop

from .server import Server
from .utils import LOG_LEVEL
from .config import Config
from .utils import create_logger
from .arbiter import Arbiter


def run(
    app_factory,
    host: str = "127.0.0.1",
    port: int = 5000,
    backlog: Optional[int] = 1024,
    workers: Optional[int] = None,
    ssl_cert_file: Optional[str] = None,
    ssl_key_file: Optional[str] = None,
    log_level: LOG_LEVEL = "INFO",
    access_log: bool = True,
    lifespan: bool = True,
):
    config = Config(
        host=host,
        port=port,
        backlog=backlog,
        workers=workers,
        ssl_key_file=ssl_key_file,
        ssl_cert_file=ssl_cert_file,
        log_level=log_level,
        access_log=access_log,
        lifespan=lifespan,
    )

    if config.workers is None:
        uvloop.install()
        (logger, access_logger) = (
            create_logger("asgi.internal", log_level),
            create_logger("asgi.access", "INFO"),
        )
        server = Server(
            app_factory=app_factory,
            config=config,
            stop_event=asyncio.Event(),
            logger=logger,
            access_logger=access_logger,
        )

        try:
            asyncio.run(server.main(config.socket))
        except KeyboardInterrupt:
            logger.info("Server is stopping...")

    else:
        arbiter = Arbiter(
            app_factory=app_factory,
            config=config,
            logger=create_logger("asgi.internal", config.log_level),
        )
        arbiter.start()
