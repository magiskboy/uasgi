from __future__ import annotations

import os
import socket
import asyncio
from typing import List, Set, TYPE_CHECKING

from .utils import create_logger
from .protocol import H11Protocol
from .lifespan import Lifespan


if TYPE_CHECKING:
    from .worker import Worker
    from .uhttp import ASGIHandler
    from .config import Config


class ServerState:
    def __init__(self, lifespan: "Lifespan"):
        self.connections: Set[asyncio.Protocol] = set()
        self.tasks: Set[asyncio.Task] = set()
        self.root_path = os.getcwd()
        self.lifespan: "Lifespan" = lifespan


class Server:
    def __init__(
        self,
        app: "ASGIHandler",
        config: "Config",
    ):
        self.workers: List["Worker"] = []
        self.config = config
        self.app = app
        self.server: asyncio.Server
        self.logger = create_logger(__name__, config.log_level, config.log_fmt)
        self.access_logger = create_logger(
            "uasgi.access", "INFO", config.access_log_fmt
        )
        self.lifespan = Lifespan(self.app)
        self.state = ServerState(self.lifespan)

    def run(self):
        try:
            asyncio.run(self.main(self.config.socket))
        except KeyboardInterrupt:
            self.stop()

    async def main(self, sock: socket.socket):
        """Entrypoint where server starts and runs"""
        loop = asyncio.get_running_loop()

        self.server = await loop.create_server(
            protocol_factory=self.create_protocol,
            sock=sock,
            ssl=self.config.get_ssl(),
            start_serving=False,
        )

        await self.startup()

        try:
            await self.server.serve_forever()
        except asyncio.CancelledError:
            ...
        finally:
            await self.shutdown()

    def create_protocol(
        self, loop: asyncio.AbstractEventLoop | None = None
    ) -> asyncio.Protocol:
        return H11Protocol(
            app=self.app,
            server_state=self.state,
            logger=self.logger,
            access_logger=self.access_logger,
            config=self.config,
            loop=loop,
        )

    async def startup(self):
        self.logger.debug("Server is starting up")
        if self.config.lifespan:
            await self.lifespan.startup()

    async def shutdown(self):
        self.logger.debug("Server is shutting down")
        if self.config.lifespan:
            await self.lifespan.shutdown()

        await self.server.wait_closed()

    def stop(self):
        self.logger.debug("Server is stopping")
        self.server.close()
