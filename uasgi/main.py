from __future__ import annotations

import sys
import threading
from typing import TYPE_CHECKING, Callable, Optional, cast

import uvloop

from .server import Server
from .utils import LOG_LEVEL
from .config import Config
from .utils import load_app
from .arbiter import Arbiter
from .reloader import Reloader


if TYPE_CHECKING:
    from .uhttp import ASGIHandler


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
    log_fmt: Optional[str] = None,
    access_log_fmt: Optional[str] = None,
):
    uvloop.install()

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
        access_log_fmt=access_log_fmt,
        log_fmt=log_fmt,
    )
    config.setup_socket()
    config.workers = config.workers or 1

    sys.stdout.write(str(config))

    if reloader:
        Reloader(
            app=app,  # type: ignore
            config=config,
            stop_event=threading.Event(),
        ).main()
        return

    if config.workers == 1 and not reloader:
        loaded_app = load_app(app)
        Server(
            app=loaded_app,
            config=config,
        ).run()
        return

    Arbiter(
        app=cast(Callable[[], "ASGIHandler"] | str, app),
        config=config,
    ).main()

    return
