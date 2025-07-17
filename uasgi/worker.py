from __future__ import annotations

import time
import asyncio
import threading
import multiprocessing as mp
from typing import TYPE_CHECKING

import uvloop

from .server import Server
from .utils import create_logger


if TYPE_CHECKING:
    from .config import Config


class Worker:
    def __init__(self, app_factory, config: "Config", name: str):
        self.app_factory = app_factory
        self.worker = None
        self.config = config
        self.stop_event = asyncio.Event()
        self.logger = create_logger("asgi.worker", config.log_level)
        self.access_logger = create_logger("asgi.access", "INFO")
        (self._receiver, self._sender) = mp.Pipe(duplex=False)
        self.name = name

    def run(self):
        self.worker = mp.Process(target=self.serve, name=self.name)
        self.worker.start()

    def serve(self):
        uvloop.install()

        server = Server(
            app_factory=self.app_factory,
            config=self.config,
            stop_event=self.stop_event,
            logger=self.logger,
            access_logger=self.access_logger,
        )

        alive_t = threading.Thread(target=self.alive, args=(server,))
        alive_t.start()

        asyncio.run(server.main(self.config.socket))

    def stop(self):
        self.stop_event.set()

    @property
    def pid(self):
        if self.worker:
            return self.worker.pid

    def alive(self, server: Server):
        while not self.stop_event.is_set():
            self._sender.send(
                {
                    "num_connections": len(server.state.connections),
                    "num_tasks": len(server.state.tasks),
                }
            )
            time.sleep(1)

    @property
    def receiver(self):
        return self._receiver
