from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Callable, Optional, cast

import uvloop


from .server import Server
from .utils import LOG_LEVEL
from .config import Config
from .utils import create_logger, load_app
from .arbiter import Arbiter

if TYPE_CHECKING:
    from .http import ASGIHandler


def run(
    app: str | Callable[[], "ASGIHandler"] | "ASGIHandler",
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

    loaded_app = load_app(app)

    if config.workers is None:
        uvloop.install()
        (logger, access_logger) = (
            create_logger("asgi.internal", log_level),
            create_logger("asgi.access", "INFO"),
        )
        server = Server(
            app=loaded_app,
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
        config.setup_socket()

        if asyncio.iscoroutinefunction(app):
            raise RuntimeError(
                "You must use str or factory function in worker mode"
            )

        arbiter = Arbiter(
            app=cast(Callable[[], "ASGIHandler"] | str, app),
            config=config,
            logger=create_logger("asgi.internal", config.log_level),
        )
        arbiter.start()
