from __future__ import annotations

import asyncio
import signal
from typing import Optional

import uvloop

from .server import Server
from .types import LOG_LEVEL, Config
from .utils import create_logger
from .arbiter import Arbiter


STOP_SIGNALS = [signal.SIGINT, signal.SIGHUP, signal.SIGTERM]


def on_stop_signals(handler):
    global STOP_SIGNALS
    for s in STOP_SIGNALS:
        signal.signal(s, handler)


def run(
    app_factory,
    host: str = '127.0.0.1',
    port: int = 5000,
    backlog: Optional[int] = 1024,
    workers: Optional[int] = None,
    ssl_cert_file: Optional[str] = None,
    ssl_key_file: Optional[str] = None,
    enable_h2: bool = False,
    log_level: LOG_LEVEL = 'INFO'
):
    config = Config(
        host=host,
        port=port,
        backlog=backlog,
        workers=workers,
        ssl_key_file=ssl_key_file,
        ssl_cert_file=ssl_cert_file,
        enable_h2=enable_h2,
        log_level=log_level,
    )
    config.create_socket()

    if config.workers is None:
        uvloop.install()
        logger = create_logger('asgi.internal', log_level)
        access_logger = create_logger('asgi.access', 'INFO')
        stop_event = asyncio.Event()
        config.create_socket()
        server = Server(
            app_factory=app_factory,
            config=config,
            stop_event=stop_event,
            logger=logger,
            access_logger=access_logger,
        )

        on_stop_signals(lambda *_: stop_event.set())

        asyncio.run(server.main(config.socket))

    else:

        arbiter = Arbiter(
            app_factory=app_factory,
            config=config,
            logger=create_logger('asgi.internal', config.log_level),
        )
        arbiter.start()

