from __future__ import annotations

import os
import socket
import logging
import asyncio
from typing import Callable, List, Set, TYPE_CHECKING

from .protocol import H11Protocol
from .lifespan import Lifespan

if TYPE_CHECKING:
    from .worker import Worker
    from .types import ASGIHandler
    from .config import Config


class ServerState:
    def __init__(self, lifespan: "Lifespan"):
        self.connections: Set[asyncio.Protocol] = set()
        self.tasks: Set[asyncio.Task] = set()
        self.root_path = os.getcwd()
        self.lifespan: "Lifespan" = lifespan


class Server:
    def __init__(self,
        app_factory: Callable[..., "ASGIHandler"],
        config: "Config",
        stop_event: asyncio.Event,
        logger: logging.Logger,
        access_logger: logging.Logger,
    ):
        self.app_factory = app_factory
        self.workers: List["Worker"] = []
        self.config = config
        self.app = self.app_factory()
        self.stop_event = stop_event
        self.server: asyncio.Server
        self.logger = logger
        self.access_logger = access_logger
        self.lifespan = Lifespan(self.app)
        self.state = ServerState(self.lifespan)

    async def main(self, sock: socket.socket):
        self.logger.info(f"Worker {self.pid} is running...")

        loop = asyncio.get_running_loop()

        self.server = await loop.create_server(
            protocol_factory=self.create_protocol,
            sock=sock,
            ssl=self.config.get_ssl(),
            start_serving=False,
        )

        await self.startup()

        stop_event_task = asyncio.create_task(self.stop_event.wait())
        server_listen_task = asyncio.create_task(self.server.serve_forever())
        gather = asyncio.wait(
            fs=[stop_event_task, server_listen_task],
            return_when=asyncio.FIRST_COMPLETED,
        )
        try:
            await gather
        except asyncio.CancelledError:
            ...

        await self.shutdown()

    def create_protocol(self, _: asyncio.AbstractEventLoop | None = None) -> asyncio.Protocol:
        return H11Protocol(
            app=self.app,
            server_state=self.state,
            logger=self.logger,
            access_logger=self.access_logger,
            config=self.config,
        )

    async def startup(self):
        if self.config.lifespan:
            await self.lifespan.startup()

    async def shutdown(self):
        if self.config.lifespan:
            await self.lifespan.shutdown()
    
    @property
    def pid(self):
        return os.getpid()

