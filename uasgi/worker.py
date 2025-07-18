from __future__ import annotations

import asyncio
import multiprocessing as mp
from typing import TYPE_CHECKING, Optional

import uvloop

from .server import Server
from .utils import create_logger, load_app


if TYPE_CHECKING:
    from .config import Config


class Worker:
    def __init__(self, app, config: "Config", name: str):
        self.app = app
        self.worker = None
        self.config = config
        self.logger = create_logger("asgi.worker", config.log_level)
        self.access_logger = create_logger("asgi.access", "INFO")
        self.name = name
        self.server: Optional[Server] = None

    def run(self):
        self.worker = mp.Process(
            target=self.serve, name=self.name, daemon=True
        )
        self.worker.start()

    def serve(self):
        uvloop.install()

        app = load_app(self.app)
        server = Server(
            app=app,
            config=self.config,
            logger=self.logger,
            access_logger=self.access_logger,
        )

        asyncio.run(server.main(self.config.socket))

    def stop(self):
        if self.server:
            self.server.stop()

    @property
    def pid(self):
        if self.worker:
            return self.worker.pid

    def reload(self):
        self.logger.info("Reloading...")
