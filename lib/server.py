import os
import socket
import logging
import asyncio
from typing import List
import typing

from .protocol import HTTPProtocol
from .types import Config


if typing.TYPE_CHECKING:
    from .worker import Worker


class Server:
    def __init__(self, app_factory, config: Config):
        self.app_factory = app_factory
        self.workers: List["Worker"] = []
        self.config = config
        self.app = self.app_factory()

        self.setup()

    def setup(self):
        self.logger = logging.getLogger('server.internal')
        self.logger.setLevel(logging.DEBUG)
        handler = logging.StreamHandler()
        fmt = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        handler.setFormatter(fmt)
        self.logger.addHandler(handler)

        self.config.create_socket()

    def run(self):
        """Important!!! Only run in the main process"""

        self.sock = self.config.sock
        host, port = self.config.socket.getsockname() #type: ignore

        self.logger.info(f"Server is starting at {host}:{port}")
        if self.config.workers is None:
            import uvloop
            uvloop.install()
            asyncio.run(self.serve(self.config.socket))
            return

        from .worker import Worker
        for _ in range(self.config.workers):
            worker = Worker(self.app_factory, self.config)
            worker.run()
            self.workers.append(worker)

        for worker in self.workers:
            worker.join()

    async def serve(self, sock: socket.socket):
        self.logger.info(f"Worker {self.pid} is running...")

        loop = asyncio.get_running_loop()
        _server = await loop.create_server(
            protocol_factory=self.create_protocol,
            sock=sock,
        )
        await _server.serve_forever()

    def create_protocol(self, _: asyncio.AbstractEventLoop | None = None) -> asyncio.Protocol:
        return HTTPProtocol(self.app)
    
    @property
    def pid(self):
        return os.getpid()

