from __future__ import annotations

import sys
from typing import TYPE_CHECKING, Callable, Optional

import uvloop

from uasgi.worker import Worker

from .config import Config
from .arbiter import Arbiter


if TYPE_CHECKING:
    from .uhttp import ASGIHandler
    from .utils import LOG_LEVEL


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
    reload: Optional[bool] = False,
    log_fmt: Optional[str] = None,
    access_log_fmt: Optional[str] = None,
):
    uvloop.install()

    config = Config(
        app,
        host=host,
        port=port,
        backlog=backlog,
        workers=workers,
        ssl_key_file=ssl_key_file,
        ssl_cert_file=ssl_cert_file,
        log_level=log_level,
        access_log=access_log,
        lifespan=lifespan,
        access_log_fmt=access_log_fmt,
        log_fmt=log_fmt,
        reload=reload,
    )
    config.setup_socket()

    sys.stdout.write(str(config))

    if config.workers == 1:
        return Worker(
            config=config,
        ).run(blocking=True)

    Arbiter(
        config=config,
    ).main()

    return
