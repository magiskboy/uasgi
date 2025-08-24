from __future__ import annotations

import os
import socket
import asyncio
from typing import Set, TYPE_CHECKING

from .utils import create_logger
from .protocol import H11Protocol
from .h2_protocol import H2Protocol
from .lifespan import Lifespan


if TYPE_CHECKING:
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
        self.config = config
        self.app = app
        self.server: asyncio.Server
        self.logger = create_logger(__name__, config.log_level, config.log_fmt)
        self.access_logger = create_logger(
            "uasgi.access", "INFO", config.access_log_fmt
        )
        self.lifespan = Lifespan(self.app)
        self.state = ServerState(self.lifespan)

    def main(self):
        """Entrypoint where server starts and runs"""

        if self.config.socket is None:
            raise RuntimeError("Socket must be binded before starting server")

        asyncio.run(self.run(self.config.socket))

    async def run(self, sock: socket.socket):
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
        if self.config.protocol == "h11":
            return H11Protocol(
                app=self.app,
                server_state=self.state,
                logger=self.logger,
                access_logger=self.access_logger,
                config=self.config,
                loop=loop,
            )

        if self.config.protocol == "h2":
            return H2Protocol(
                app=self.app,
                server_state=self.state,
            )

        raise RuntimeError(f"{self.config.protocol} is not support")

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
