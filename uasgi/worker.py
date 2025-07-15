from __future__ import annotations

import os
import asyncio
import multiprocessing as mp

import uvloop

from .server import Server
from .types import Config
from .utils import create_logger


class Worker:
    def __init__(self, app_factory, config: Config):
        self.app_factory = app_factory
        self.worker = None
        self.config = config
        self.stop_event = asyncio.Event()
        self.logger = create_logger('asgi.internal', config.log_level)
        self.access_logger = create_logger('asgi.access', 'INFO')

    def run(self):
        self.worker = mp.Process(target=self.serve)
        self.worker.start()

    def serve(self):
        uvloop.install()

        self.logger.info(f"Worker {self.pid} is running...")
        self.config.create_socket()
        server = Server(
            app_factory=self.app_factory,
            config=self.config,
            stop_event=self.stop_event,
            logger=self.logger,
            access_logger=self.access_logger,
        )
        asyncio.run(server.main(self.config.socket))

    def stop(self):
        self.logger.info(f"Worker {self.pid} is stopping...")
        self.stop_event.set()

    @property
    def pid(self):
        return os.getpid()

    def alive(self):
        ...
