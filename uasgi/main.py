from __future__ import annotations

import asyncio
import signal
from typing import TYPE_CHECKING, Callable, Optional, cast
import threading

import uvloop

from .server import Server
from .utils import LOG_LEVEL
from .config import Config
from .utils import create_logger, load_app
from .arbiter import Arbiter
from .reloader import Reloader


if TYPE_CHECKING:
    from .uhttp import ASGIHandler


uvloop.install()


def run(
    app: str | Callable[[], "ASGIHandler"] | "ASGIHandler",
    host: str = "127.0.0.1",
    port: int = 5000,
    backlog: Optional[int] = 1024,
    workers: Optional[int] = 1,
    ssl_cert_file: Optional[str] = None,
    ssl_key_file: Optional[str] = None,
    log_level: LOG_LEVEL = "INFO",
    access_log: bool = True,
    lifespan: bool = True,
    reloader: Optional[bool] = False,
):
    _reloader: Optional[Reloader] = None
    _server: Optional[Server] = None
    _arbiter: Optional[Arbiter] = None

    def on_exit(*_):
        if _reloader:
            _reloader.stop()

        if _server:
            _server.stop()

        if _arbiter:
            _arbiter.stop()

    signal.signal(signal.SIGTERM, on_exit)
    signal.signal(signal.SIGQUIT, on_exit)
    signal.signal(signal.SIGINT, on_exit)

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
    config.setup_socket()
    config.workers = config.workers or 1

    if config.workers > 1 and reloader:
        raise RuntimeError(
            "Number of workers must equals to 1 in reloader mode."
        )

    logger = create_logger("asgi.access", "INFO")
    access_logger = create_logger("asgi.internal", log_level)

    if config.workers == 1 and reloader:
        _reloader = Reloader(
            app=app,  # type: ignore
            config=config,
            stop_event=threading.Event(),
            logger=logger,
        )

        try:
            _reloader.run()
        except KeyboardInterrupt:
            logger.info("Server is stopping...")

        return

    if config.workers == 1 and not reloader:
        loaded_app = load_app(app)
        _server = Server(
            app=loaded_app,
            config=config,
            logger=logger,
            access_logger=access_logger,
        )

        try:
            asyncio.run(_server.main(config.socket))
        except KeyboardInterrupt:
            _server.stop()
            logger.info("Server is stopping...")

        return

    if asyncio.iscoroutinefunction(app):
        raise RuntimeError(
            "You must use str or factory function in worker mode"
        )

    _arbiter = Arbiter(
        app=cast(Callable[[], "ASGIHandler"] | str, app),
        config=config,
        logger=create_logger("asgi.internal", config.log_level),
    )
    _arbiter.start()
    return
