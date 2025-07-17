from __future__ import annotations

import logging
import asyncio
import urllib.parse
from collections import deque
from typing import TYPE_CHECKING, List, Literal, Optional, Set, Tuple

import httptools

from .uhttp import HTTPScope, HttpScopeRunner, ASGIHandler

if TYPE_CHECKING:
    from .server import ServerState
    from .config import Config


NO_BODY_METHOD = {
    "GET",
    "OPTIONS",
    "HEAD",
}


class H11Protocol(asyncio.Protocol):
    def __init__(
        self,
        app,
        server_state: "ServerState",
        logger: logging.Logger,
        access_logger: logging.Logger,
        config: "Config",
        loop: Optional[asyncio.AbstractEventLoop],
    ):
        # global scope
        self.app: "ASGIHandler" = app
        self.tasks: Set[asyncio.Task] = server_state.tasks
        self.connections: Set[asyncio.Protocol] = server_state.connections
        self.loop: asyncio.AbstractEventLoop = (
            loop or asyncio.get_running_loop()
        )
        self.lifespan = server_state.lifespan
        self.server_state = server_state
        self.logger = logger
        self.access_logger = access_logger
        self.config = config

        # connection scope
        self.parser = httptools.HttpRequestParser(self)  # type: ignore
        self.parser.set_dangerous_leniencies(lenient_data_after_close=True)
        self.client: Tuple[str, int]
        self.server: Tuple[str, int]
        self.transport: asyncio.Transport
        self.pipeline: deque["HttpScopeRunner"] = deque()
        self.ready_write: asyncio.Event

        # request state
        self.url: bytes
        self.scope: "HTTPScope"
        self.scheme: Optional[Literal["https", "http", "ws", "wss"]]
        self.headers: List[Tuple[bytes, bytes]]
        self.current_runner: Optional["HttpScopeRunner"] = None

    def connection_made(self, transport: asyncio.Transport) -> None:  # type:ignore
        self.transport = transport
        self.server = transport.get_extra_info("socket").getsockname()
        self.client = transport.get_extra_info("peername")
        self.ssl = transport.get_extra_info("sslcontext")
        self.ready_write = asyncio.Event()
        self.ready_write.set()
        if self.ssl:
            self.scheme = "https"
        else:
            self.scheme = "http"

    def pause_writing(self) -> None:
        self.ready_write.clear()

    def resume_writing(self) -> None:
        self.ready_write.set()

    def connection_lost(self, exc: Exception | None) -> None:
        self.connections.discard(self)
        return super().connection_lost(exc)

    def data_received(self, data: bytes) -> None:
        self.parser.feed_data(data)

    # -------------------- for parser ------------------------
    def on_url(self, url: bytes):
        self.url += url

    def on_message_begin(self):
        self.url = b""
        self.headers = []

        self.scope = {
            "method": b"",
            "query_string": b"",
            "path": "",
            "type": "http",
            "asgi": {
                "version": "2.5",
                "spec_version": "2.0",
            },
            "raw_path": None,
            "scheme": self.scheme,
            "http_version": "1.1",
            "root_path": self.server_state.root_path,
            "headers": self.headers,
            "client": self.client,
            "server": self.server,
            "state": self.lifespan.app_state,
        }

    def on_header(self, name: bytes, value: bytes):
        self.headers.append((name, value))

    def on_headers_complete(self):
        parsed_url = httptools.parse_url(self.url)  # type: ignore
        raw_path = parsed_url.path
        path = raw_path.decode("ascii")
        if "%" in path:
            path = urllib.parse.unquote(path)

        self.scope["method"] = self.parser.get_method().decode("ascii")
        self.scope["path"] = path
        self.scope["raw_path"] = raw_path
        self.scope["query_string"] = parsed_url.query or b""

        runner = HttpScopeRunner(
            scope=self.scope,
            app=self.app,
            transport=self.transport,
            message_event=asyncio.Event(),
            message_complete=self.scope["method"] in NO_BODY_METHOD,
            on_response_complete=self.on_response_complete,
            ready_write=self.ready_write,
            config=self.config,
            access_logger=self.access_logger,
        )

        if self.current_runner:
            self.pipeline.appendleft(runner)

        else:
            self.current_runner = runner
            self.schedule_runner(runner)

    def schedule_runner(self, runner: "HttpScopeRunner"):
        task = self.loop.create_task(runner.run())
        runner.task = task
        task.add_done_callback(self.tasks.discard)
        self.tasks.add(task)

    def on_response_complete(self):
        self.current_runner = None

        if self.pipeline:
            runner = self.pipeline.pop()
            self.schedule_runner(runner)

    def on_body(self, body: bytes):
        if self.current_runner:
            self.current_runner.set_body(body)

    def on_message_complete(self):
        if self.current_runner:
            self.current_runner.message_complete = True
