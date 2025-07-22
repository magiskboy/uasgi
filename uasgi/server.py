from __future__ import annotations

import os
import asyncio
import sys
from typing import List, Set, TYPE_CHECKING, Union

from .utils import create_logger, load_app
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
        app: Union["ASGIHandler", str],
        config: "Config",
    ):
        self.workers: List["Worker"] = []
        self.config = config
        self.old_app = None
        self._initialized_modules = set()

        if isinstance(app, str):
            for key in sys.modules.keys():
                self._initialized_modules.add(key)

            self.app = load_app(app)
            self.app_str = app
        else:
            self.app = app
            self.app_str = None

        self.lifespan = Lifespan(self.app)
        self.state = ServerState(self.lifespan)

        self.server: asyncio.Server
        self.logger = create_logger(__name__, config.log_level, config.log_fmt)
        self.access_logger = create_logger(
            "uasgi.access", "INFO", config.access_log_fmt
        )
        self._stop_event = asyncio.Event()
        self._reload_event = asyncio.Event()

    def run(self):
        try:
            asyncio.run(self.main())
        except KeyboardInterrupt:
            self.stop()

    async def main(self):
        """Entrypoint where server starts and runs"""
        loop = asyncio.get_running_loop()

        while not self._stop_event.is_set():
            self._reload_event.clear()

            self.server = await loop.create_server(
                protocol_factory=self.create_protocol,
                sock=self.config.socket,
                ssl=self.config.get_ssl(),
                start_serving=False,
            )

            await self.startup()

            await self.server.start_serving()

            try:
                await self._reload_event.wait()
                self.config.sock = self.config.create_socket()
            except KeyboardInterrupt:
                break
            finally:
                await self.shutdown()
                self.server.close()
                await self.server.wait_closed()

            if self.app_str:
                keys = set(sys.modules.keys()).difference(
                    self._initialized_modules
                )
                for key in keys:
                    sys.modules.pop(key)
                self.app = load_app(self.app_str)
            self.lifespan = Lifespan(self.app)
            self.state.lifespan = self.lifespan

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

    def stop(self):
        self.logger.debug("Server is stopping")
        self._stop_event.set()

    def reload(self):
        self._reload_event.set()
